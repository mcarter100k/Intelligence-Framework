//+------------------------------------------------------------------+
//|  TradeLogger.mq5                                                 |
//|  Sends every GBP/AUD trade open/close to the Intelligence        |
//|  Framework running on your Mac.                                  |
//|                                                                  |
//|  SETUP (one time):                                               |
//|  1. MT5 → Tools → Options → Expert Advisors                      |
//|  2. Tick "Allow WebRequest for listed URL"                       |
//|  3. Add:  http://localhost:5001                                  |
//|  4. Compile this EA (F7 in MetaEditor)                          |
//|  5. Drag onto your GBP/AUD chart from the Navigator panel        |
//|  6. Start trade_receiver.py before you begin trading             |
//+------------------------------------------------------------------+
#property copyright "Intelligence Framework"
#property version   "1.0"
#property strict

input string ServerURL  = "http://localhost:5001";   // Framework server address
input string PairFilter = "GBPAUD";                  // Only log this symbol

//--- Ping the server on startup so you know the connection works
int OnInit()
  {
   string payload = "{\"type\":\"ping\",\"source\":\"TradeLogger\"}";
   bool ok = SendToServer(payload);
   if(ok)
      Print("TradeLogger: Connected to Intelligence Framework on ", ServerURL);
   else
      Print("TradeLogger: Could not reach server at ", ServerURL,
            " — start trade_receiver.py before trading");
   return(INIT_SUCCEEDED);
  }

//--- Fire on every deal event
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest     &request,
                        const MqlTradeResult      &result)
  {
   //--- Only care about deals being added (not order state changes)
   if(trans.type != TRADE_TRANSACTION_DEAL_ADD) return;

   //--- Only log the target pair
   string sym = trans.symbol;
   if(StringFind(sym, PairFilter) < 0) return;

   ulong ticket = trans.deal;

   //--- Make sure the deal is in history before reading it
   HistorySelect(TimeCurrent() - 120, TimeCurrent() + 1);
   if(!HistoryDealSelect(ticket)) return;

   //--- Read deal fields
   ENUM_DEAL_ENTRY entry_type = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(ticket, DEAL_ENTRY);
   ENUM_DEAL_TYPE  deal_type  = (ENUM_DEAL_TYPE) HistoryDealGetInteger(ticket, DEAL_TYPE);

   //--- Only handle position opens and closes (skip internal transfers)
   if(entry_type != DEAL_ENTRY_IN && entry_type != DEAL_ENTRY_OUT) return;

   ulong    pos_id     = HistoryDealGetInteger(ticket, DEAL_POSITION_ID);
   double   price      = HistoryDealGetDouble (ticket, DEAL_PRICE);
   double   volume     = HistoryDealGetDouble (ticket, DEAL_VOLUME);
   double   profit     = HistoryDealGetDouble (ticket, DEAL_PROFIT);
   double   commission = HistoryDealGetDouble (ticket, DEAL_COMMISSION);
   double   swap       = HistoryDealGetDouble (ticket, DEAL_SWAP);
   datetime deal_time  = (datetime)HistoryDealGetInteger(ticket, DEAL_TIME);

   string event_type = (entry_type == DEAL_ENTRY_IN) ? "OPEN" : "CLOSE";
   string direction  = (deal_type  == DEAL_TYPE_BUY) ? "BUY"  : "SELL";
   string time_str   = TimeToString(deal_time, TIME_DATE | TIME_MINUTES | TIME_SECONDS);

   //--- Build JSON payload
   string payload = StringFormat(
      "{\"type\":\"%s\","
      "\"ticket\":%I64u,"
      "\"position_id\":%I64u,"
      "\"symbol\":\"%s\","
      "\"direction\":\"%s\","
      "\"price\":%.5f,"
      "\"volume\":%.2f,"
      "\"profit\":%.2f,"
      "\"commission\":%.2f,"
      "\"swap\":%.2f,"
      "\"time\":\"%s\"}",
      event_type,
      ticket,
      pos_id,
      sym,
      direction,
      price,
      volume,
      profit,
      commission,
      swap,
      time_str
   );

   if(SendToServer(payload))
      Print("TradeLogger [", event_type, "] ", sym, " ", direction,
            " @ ", DoubleToString(price, 5),
            "  profit=", DoubleToString(profit, 2));
  }

//--- HTTP POST helper
bool SendToServer(string payload)
  {
   string url     = ServerURL + "/trade";
   string headers = "Content-Type: application/json\r\n";
   char   post_data[];
   char   result_data[];
   string result_headers;

   int len = StringLen(payload);
   ArrayResize(post_data, len);
   StringToCharArray(payload, post_data, 0, len);

   int res = WebRequest("POST", url, headers, 5000,
                        post_data, result_data, result_headers);
   return(res >= 200 && res < 300);
  }
//+------------------------------------------------------------------+
