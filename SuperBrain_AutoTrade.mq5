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
      + StringFormat("   OPEN TRADES    : %d\n", PositionsTotal())
      + StringFormat("   MAGIC NUMBER   : %d\n", InpMagicNumber)
      + " ========================================================\n"
      + "   Connected to: TheSmartMag Quant Multi-Model AI       \n"
      + " ========================================================\n";

   Comment(hud);
  }
//+------------------------------------------------------------------+
