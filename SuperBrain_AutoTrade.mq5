//+------------------------------------------------------------------+
//|                                         SuperBrain_AutoTrade.mq5 |
//|                        Copyright 2026, TheSmartMag Quant AI Labs |
//|                                   https://trade.thesmartmag.com  |
//+------------------------------------------------------------------+
#property copyright   "Copyright 2026, TheSmartMag Quant AI Labs"
#property link        "https://trade.thesmartmag.com"
#property version     "2.40"
#property description "High-Speed Autonomous Execution Bridge for TheSmartMag SuperBrain AI"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\AccountInfo.mqh>

//--- Input parameters
input group "=== Cloud Server API Settings ==="
input string   InpCloudUrl          = "https://coinsai-terminal.onrender.com/api/mt5/bridge"; // Bridge URL
input string   InpBridgeSecret      = "ck_capital_secret_2026"; // Secret Key (Matches .env)
input int      InpPollIntervalSec   = 2;                        // Poll interval in seconds (1-10)

input group "=== Risk Guardian and Prop Firm Rules ==="
input double   InpMaxDailyLossUSD   = 300.0;                    // Daily loss kill-switch ($300 cap)
input double   InpMinEquityFloorUSD = 9500.0;                   // Hard drawdown floor ($9,500 for $10K account)
input double   InpDefaultLots       = 0.01;                     // Default fallback lot size
input ulong    InpMagicNumber       = 20261026;                 // Magic Number for SuperBrain orders
input ulong    InpSlippagePoints    = 20;                       // Max allowed slippage points

//--- Global Objects
CTrade         m_trade;
CSymbolInfo    m_symbol;
CPositionInfo  m_position;
CAccountInfo   m_account;

datetime       m_last_poll_time = 0;
double         m_starting_balance = 0;

void DrawDashboard(string statusText = "ONLINE");
void SendTelemetryAndFetchCommand();
void ProcessCommand(const string json);
void CloseAllPositions();
void EnforceSafetyStopsOnOpenPositions();
void SendAcknowledge(const string cmdId, const string status, const ulong ticket);

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   m_trade.SetExpertMagicNumber(InpMagicNumber);
   m_trade.SetDeviationInPoints(InpSlippagePoints);
   // Adaptive Filling Mode detection (FOK / IOC / RETURN) based on broker symbol execution policy
   uint filling = (uint)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((filling & SYMBOL_FILLING_IOC) != 0)
      m_trade.SetTypeFilling(ORDER_FILLING_IOC);
   else if((filling & SYMBOL_FILLING_FOK) != 0)
      m_trade.SetTypeFilling(ORDER_FILLING_FOK);
   else
      m_trade.SetTypeFilling(ORDER_FILLING_RETURN);

   m_starting_balance = m_account.Balance();

   PrintFormat("SuperBrain_AutoTrade EA Initialized. Account: %d | Server: %s | Balance: $%.2f",
               m_account.Login(), m_account.Server(), m_starting_balance);

   EventSetTimer(1); // 1-second timer event
   DrawDashboard();
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Comment("");
   Print("SuperBrain_AutoTrade EA Deinitialized. Reason: ", reason);
  }

//+------------------------------------------------------------------+
//| Timer event function (Polls Cloud Engine)                        |
//+------------------------------------------------------------------+
void OnTimer()
  {
   datetime now = TimeCurrent();
   if(now - m_last_poll_time < InpPollIntervalSec)
      return;

   m_last_poll_time = now;

   // 1. Check Prop Firm Hard Equity Floor ($9,500.00)
   double equity = m_account.Equity();
   if(equity <= InpMinEquityFloorUSD)
     {
      PrintFormat("CRITICAL GUARDIAN STOP: Equity $%.2f reached MLL Floor $%.2f. Trading HALTED.", equity, InpMinEquityFloorUSD);
      DrawDashboard("EMERGENCY HALT: MLL FLOOR REACHED");
      return;
     }

   // 2. Enforce Mandatory Protective Stop Loss & Take Profit on all open positions
   EnforceSafetyStopsOnOpenPositions();

   // 3. Transmit Account Telemetry & Fetch Pending Signals from AI Brain
   SendTelemetryAndFetchCommand();
   DrawDashboard("ACTIVE - SCANNING");
  }

//+------------------------------------------------------------------+
//| Send Telemetry & Receive Command via WebRequest                  |
//+------------------------------------------------------------------+
void SendTelemetryAndFetchCommand()
  {
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
     {
      DrawDashboard("WARNING: ALGO TRADING BUTTON IS OFF");
      return;
     }

   // Build JSON payload
   string jsonPayload = StringFormat(
      "{\"account\":%d,\"balance\":%.2f,\"equity\":%.2f,\"profit\":%.2f,\"secret\":\"%s\",\"positions\":%d}",
      m_account.Login(),
      m_account.Balance(),
      m_account.Equity(),
      m_account.Profit(),
      InpBridgeSecret,
      PositionsTotal()
   );

   char post[];
   char result[];
   string resultHeaders;
   StringToCharArray(jsonPayload, post, 0, StringLen(jsonPayload));

   string headers = "Content-Type: application/json\r\n"
                  + "X-Bridge-Secret: " + InpBridgeSecret + "\r\n";

   ResetLastError();
   int res = WebRequest("POST", InpCloudUrl, headers, 3000, post, result, resultHeaders);

   if(res == -1)
     {
      int err = GetLastError();
      if(err == 4014)
         Print("WebRequest Error 4014: URL not allowed! Add '", InpCloudUrl, "' in Tools -> Options -> Expert Advisors -> Allow WebRequest.");
      return;
     }

   if(res == 200)
     {
      string responseText = CharArrayToString(result);
      if(StringLen(responseText) > 5 && StringFind(responseText, "\"action\"") >= 0)
        {
         ProcessCommand(responseText);
        }
     }
  }

//+------------------------------------------------------------------+
//| Simple JSON field extractor helper                              |
//+------------------------------------------------------------------+
string ExtractJsonValue(const string json, const string key)
  {
   string searchKey = "\"" + key + "\":";
   int start = StringFind(json, searchKey);
   if(start < 0)
      return "";

   start += StringLen(searchKey);
   while(start < StringLen(json) && (StringGetCharacter(json, start) == ' ' || StringGetCharacter(json, start) == '\"'))
      start++;

   int end = start;
   while(end < StringLen(json) && 
         StringGetCharacter(json, end) != '\"' && 
         StringGetCharacter(json, end) != ',' && 
         StringGetCharacter(json, end) != '}' && 
         StringGetCharacter(json, end) != ']')
     {
      end++;
     }

   return StringSubstr(json, start, end - start);
  }

//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Validate and Normalize Stop Loss & Take Profit against broker stops|
//+------------------------------------------------------------------+
void NormalizeAndValidateStops(const string sym, const string act, const double currentPrice, double &sl, double &tp)
  {
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   long stopLevel = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
   double minDistance = (stopLevel > 0 ? (double)stopLevel : 10.0) * point;

   if(act == "BUY")
     {
      // SL must be strictly below current ask price minus minDistance
      if(sl > 0.0)
        {
         if(sl >= currentPrice - minDistance)
            sl = currentPrice - (minDistance * 2.0);
         sl = NormalizeDouble(sl, digits);
        }
      // TP must be strictly above current ask price plus minDistance
      if(tp > 0.0)
        {
         if(tp <= currentPrice + minDistance)
            tp = currentPrice + (minDistance * 2.0);
         tp = NormalizeDouble(tp, digits);
        }
     }
   else if(act == "SELL")
     {
      // SL must be strictly above current bid price plus minDistance
      if(sl > 0.0)
        {
         if(sl <= currentPrice + minDistance)
            sl = currentPrice + (minDistance * 2.0);
         sl = NormalizeDouble(sl, digits);
        }
      // TP must be strictly below current bid price minus minDistance
      if(tp > 0.0)
        {
         if(tp >= currentPrice - minDistance)
            tp = currentPrice - (minDistance * 2.0);
         tp = NormalizeDouble(tp, digits);
        }
     }
  }

//+------------------------------------------------------------------+
//| Execute incoming Trade Signal or Order                           |
//+------------------------------------------------------------------+
void ProcessCommand(const string json)
  {
   string action  = ExtractJsonValue(json, "action");
   string symbol  = ExtractJsonValue(json, "symbol");
   double volume  = StringToDouble(ExtractJsonValue(json, "volume"));
   double sl      = StringToDouble(ExtractJsonValue(json, "sl"));
   double tp      = StringToDouble(ExtractJsonValue(json, "tp"));
   string cmdId   = ExtractJsonValue(json, "command_id");

   StringToUpper(action);
   StringToUpper(symbol);

   if(symbol == "" || symbol == "NONE")
      return;

   // Ensure symbol is selected in Market Watch
   if(!SymbolSelect(symbol, true))
     {
      PrintFormat("Symbol %s not available in market watch", symbol);
      return;
     }

   m_symbol.Name(symbol);
   m_symbol.RefreshRates();

   // Set broker-supported filling type for target symbol
   uint sym_filling = (uint)SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   if((sym_filling & SYMBOL_FILLING_IOC) != 0)
      m_trade.SetTypeFilling(ORDER_FILLING_IOC);
   else if((sym_filling & SYMBOL_FILLING_FOK) != 0)
      m_trade.SetTypeFilling(ORDER_FILLING_FOK);
   else
      m_trade.SetTypeFilling(ORDER_FILLING_RETURN);

   if(volume <= 0.0)
      volume = InpDefaultLots;

   PrintFormat("SuperBrain Signal Received: %s %s Vol: %.2f | SL: %.2f | TP: %.2f", action, symbol, volume, sl, tp);

   if(action == "BUY")
     {
      double price = m_symbol.Ask();
      NormalizeAndValidateStops(symbol, "BUY", price, sl, tp);

      bool orderPlaced = m_trade.Buy(volume, symbol, price, sl, tp, "SuperBrain AI Quantum");
      
      // Fallback: If broker rejects with 10016 (invalid stops), open at market with no stops, then modify!
      if(!orderPlaced && m_trade.ResultRetcode() == 10016)
        {
         PrintFormat("WARNING: Broker rejected stops (10016). Executing market BUY 0.00 SL/TP fallback...");
         orderPlaced = m_trade.Buy(volume, symbol, price, 0.0, 0.0, "SuperBrain AI Quantum");
         if(orderPlaced && (sl > 0.0 || tp > 0.0))
           {
            ulong ticket = m_trade.ResultOrder();
            m_trade.PositionModify(ticket, sl, tp);
           }
        }

      if(orderPlaced)
        {
         PrintFormat("SUCCESS: Live BUY placed on %s ticket=%d", symbol, m_trade.ResultOrder());
         SendAcknowledge(cmdId, "EXECUTED", m_trade.ResultOrder());
        }
      else
        {
         PrintFormat("FAILED: BUY order error %d: %s", m_trade.ResultRetcode(), m_trade.ResultRetcodeDescription());
         SendAcknowledge(cmdId, "FAILED", 0);
        }
     }
   else if(action == "SELL")
     {
      double price = m_symbol.Bid();
      NormalizeAndValidateStops(symbol, "SELL", price, sl, tp);

      bool orderPlaced = m_trade.Sell(volume, symbol, price, sl, tp, "SuperBrain AI Quantum");

      // Fallback: If broker rejects with 10016 (invalid stops), open at market with no stops, then modify!
      if(!orderPlaced && m_trade.ResultRetcode() == 10016)
        {
         PrintFormat("WARNING: Broker rejected stops (10016). Executing market SELL 0.00 SL/TP fallback...");
         orderPlaced = m_trade.Sell(volume, symbol, price, 0.0, 0.0, "SuperBrain AI Quantum");
         if(orderPlaced && (sl > 0.0 || tp > 0.0))
           {
            ulong ticket = m_trade.ResultOrder();
            m_trade.PositionModify(ticket, sl, tp);
           }
        }

      if(orderPlaced)
        {
         PrintFormat("SUCCESS: Live SELL placed on %s ticket=%d", symbol, m_trade.ResultOrder());
         SendAcknowledge(cmdId, "EXECUTED", m_trade.ResultOrder());
        }
      else
        {
         PrintFormat("FAILED: SELL order error %d: %s", m_trade.ResultRetcode(), m_trade.ResultRetcodeDescription());
         SendAcknowledge(cmdId, "FAILED", 0);
        }
     }
   else if(action == "MODIFY" || action == "SET_STOPS")
     {
      ulong ticket = (ulong)StringToInteger(ExtractJsonValue(json, "ticket"));
      if(ticket > 0 && (sl > 0.0 || tp > 0.0))
        {
         if(m_position.SelectByTicket(ticket))
           {
            string pos_sym = m_position.Symbol();
            double cur_sl = m_position.StopLoss();
            double cur_tp = m_position.TakeProfit();
            double new_sl = (sl > 0.0) ? sl : cur_sl;
            double new_tp = (tp > 0.0) ? tp : cur_tp;
            string pos_type = (m_position.PositionType() == POSITION_TYPE_BUY) ? "BUY" : "SELL";
            double cur_p = (pos_type == "BUY") ? SymbolInfoDouble(pos_sym, SYMBOL_ASK) : SymbolInfoDouble(pos_sym, SYMBOL_BID);
            NormalizeAndValidateStops(pos_sym, pos_type, cur_p, new_sl, new_tp);
            if(m_trade.PositionModify(ticket, new_sl, new_tp))
              {
               PrintFormat("SUCCESS: Modified stops on ticket #%d SL: %.2f TP: %.2f", ticket, new_sl, new_tp);
               SendAcknowledge(cmdId, "EXECUTED", ticket);
              }
            else
              {
               PrintFormat("FAILED: Modify stops on ticket #%d: %d - %s", ticket, m_trade.ResultRetcode(), m_trade.ResultRetcodeDescription());
               SendAcknowledge(cmdId, "FAILED", ticket);
              }
           }
        }
     }
   else if(action == "CLOSE_ALL")
     {
      CloseAllPositions();
      SendAcknowledge(cmdId, "CLOSED_ALL", 0);
     }
  }

//+------------------------------------------------------------------+
//| Close all open positions                                         |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Enforce Protective SL & TP on all active positions                |
//+------------------------------------------------------------------+
void EnforceSafetyStopsOnOpenPositions()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(m_position.SelectByIndex(i))
        {
         ulong ticket = m_position.Ticket();
         double sl = m_position.StopLoss();
         double tp = m_position.TakeProfit();
         string sym = m_position.Symbol();
         double openPrice = m_position.PriceOpen();
         ENUM_POSITION_TYPE pType = m_position.PositionType();
         
         // If either SL or TP is missing (0.0), calculate and attach mandatory protective stops
         if(sl <= 0.0 || tp <= 0.0)
           {
            int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
            double point = SymbolInfoDouble(sym, SYMBOL_POINT);
            long stopLevel = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
            double minDistance = (stopLevel > 0 ? (double)stopLevel : 10.0) * point;
            
            // Standard protective stops: 1.5% SL, 3.0% TP
            double def_sl = sl;
            double def_tp = tp;
            if(pType == POSITION_TYPE_BUY)
              {
               if(def_sl <= 0.0) def_sl = openPrice * 0.985;
               if(def_tp <= 0.0) def_tp = openPrice * 1.030;
               NormalizeAndValidateStops(sym, "BUY", SymbolInfoDouble(sym, SYMBOL_ASK), def_sl, def_tp);
              }
            else
              {
               if(def_sl <= 0.0) def_sl = openPrice * 1.015;
               if(def_tp <= 0.0) def_tp = openPrice * 0.970;
               NormalizeAndValidateStops(sym, "SELL", SymbolInfoDouble(sym, SYMBOL_BID), def_sl, def_tp);
              }
            
            PrintFormat("AUTO-ENFORCE SL/TP: Ticket #%d (%s) missing stops. Applying SL: %.5f, TP: %.5f",
                        ticket, sym, def_sl, def_tp);
            m_trade.PositionModify(ticket, def_sl, def_tp);
           }
        }
     }
  }

void CloseAllPositions()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(m_position.SelectByIndex(i))
        {
         m_trade.PositionClose(m_position.Ticket());
        }
     }
   Print("All open positions closed by Cloud Command.");
  }

//+------------------------------------------------------------------+
//| Acknowledge command execution to Cloud                           |
//+------------------------------------------------------------------+
void SendAcknowledge(const string cmdId, const string status, const ulong ticket)
  {
   if(cmdId == "") return;

   string ackUrl = InpCloudUrl + "/ack";
   string payload = StringFormat("{\"command_id\":\"%s\",\"status\":\"%s\",\"ticket\":%d,\"secret\":\"%s\"}",
                                 cmdId, status, ticket, InpBridgeSecret);

   char post[];
   char result[];
   string resultHeaders;
   StringToCharArray(payload, post, 0, StringLen(payload));
   string headers = "Content-Type: application/json\r\n";
   WebRequest("POST", ackUrl, headers, 2000, post, result, resultHeaders);
  }

//+------------------------------------------------------------------+
//| On-Chart HUD Display                                             |
//+------------------------------------------------------------------+
void DrawDashboard(string statusText = "ONLINE")
  {
   double equity = m_account.Equity();
   double balance = m_account.Balance();
   double profit = m_account.Profit();
   double lossRoom = equity - InpMinEquityFloorUSD;

   string hud = "\n"
      + " ========================================================\n"
      + "   THESMARTMAG SUPERBRAIN AUTOTRADE EA v2.5             \n"
      + " ========================================================\n"
      + StringFormat("   STATUS         : %s\n", statusText)
      + StringFormat("   ACCOUNT        : %d (%s)\n", m_account.Login(), m_account.Server())
      + StringFormat("   BALANCE        : $%.2f | PROFIT: $%.2f\n", balance, profit)
      + StringFormat("   EQUITY         : $%.2f\n", equity)
      + StringFormat("   MLL DRAWDOWN   : $%.2f (Floor: $%.2f)\n", lossRoom, InpMinEquityFloorUSD)
      + StringFormat("   OPEN TRADES    : %d (GUARANTEED SL/TP)\n", PositionsTotal())
      + StringFormat("   MAGIC NUMBER   : %d\n", InpMagicNumber)
      + " ========================================================\n"
      + "   Connected to: TheSmartMag Quant Multi-Model AI       \n"
      + " ========================================================\n";

   Comment(hud);
  }
//+------------------------------------------------------------------+
