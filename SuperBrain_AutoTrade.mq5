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
void SendAcknowledge(const string cmdId, const string status, const ulong ticket);

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   m_trade.SetExpertMagicNumber(InpMagicNumber);
   m_trade.SetDeviationInPoints(InpSlippagePoints);
   m_trade.SetTypeFilling(ORDER_FILLING_IOC);

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

   // 2. Transmit Account Telemetry & Fetch Pending Signals from AI Brain
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

   if(volume <= 0.0)
      volume = InpDefaultLots;

   PrintFormat("SuperBrain Signal Received: %s %s Vol: %.2f | SL: %.2f | TP: %.2f", action, symbol, volume, sl, tp);

   if(action == "BUY")
     {
      double price = m_symbol.Ask();
      if(m_trade.Buy(volume, symbol, price, sl, tp, "SuperBrain AI Quantum"))
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
      if(m_trade.Sell(volume, symbol, price, sl, tp, "SuperBrain AI Quantum"))
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
   else if(action == "CLOSE_ALL")
     {
      CloseAllPositions();
      SendAcknowledge(cmdId, "CLOSED_ALL", 0);
     }
  }

//+------------------------------------------------------------------+
//| Close all open positions                                         |
//+------------------------------------------------------------------+
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
      + " ╔══════════════════════════════════════════════════════╗\n"
      + "   THESMARTMAG SUPERBRAIN AUTOTRADE EA v2.4             \n"
      + " ╠══════════════════════════════════════════════════════╣\n"
      + StringFormat("   STATUS         : %s\n", statusText)
      + StringFormat("   ACCOUNT        : %d (%s)\n", m_account.Login(), m_account.Server())
      + StringFormat("   BALANCE        : $%.2f | PROFIT: $%.2f\n", balance, profit)
      + StringFormat("   EQUITY         : $%.2f\n", equity)
      + StringFormat("   MLL DRAWDOWN   : $%.2f (Floor: $%.2f)\n", lossRoom, InpMinEquityFloorUSD)
      + StringFormat("   OPEN TRADES    : %d\n", PositionsTotal())
      + StringFormat("   MAGIC NUMBER   : %d\n", InpMagicNumber)
      + " ╠══════════════════════════════════════════════════════╣\n"
      + "   Connected to: TheSmartMag Quant Multi-Model AI       \n"
      + " ╚══════════════════════════════════════════════════════╝\n";

   Comment(hud);
  }
//+------------------------------------------------------------------+
