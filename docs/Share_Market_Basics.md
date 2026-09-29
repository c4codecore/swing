# Share Market Seekhna Hai
### Basics se Swing Trading Strategies Tak
*Family Learning Notes*

`BASICS` &nbsp; `RISK MANAGEMENT` &nbsp; `5 STRATEGIES` &nbsp; `INDICATORS` &nbsp; `GLOSSARY`

---

## Part 1: Share Market Ke Basics

### Share / Stock Kya Hota Hai

Jab koi company grow karna chahti hai (naya factory lagana, business expand karna), use paison ki zaroorat hoti hai. Company apna ek chhota hissa (share) logon ko bechti hai — jo bhi wo share kharidta hai, wo us company ka chhota sa "owner" ban jaata hai.

> **Example**
> Agar Reliance company ke total 100 shares hain, aur aapne 1 share kharida, toh aap company ke 1% ke (chhote se) owner ban gaye.
> Company achha perform karegi toh share ki value badhegi. Company ka business kharab hoga toh value ghategi.

### Stock Exchange

Stock Exchange ek marketplace hai jahan shares kharide-beche jaate hain — bilkul sabzi mandi jaisa, bas yahan sabzi ki jagah company ke shares trade hote hain. India mein do main exchanges hain:

- NSE (National Stock Exchange) — sabse zyada use hone wala
- BSE (Bombay Stock Exchange) — India ka sabse purana exchange

### Demat Account aur Trading Account

Shares kharidne-bechne ke liye 2 cheezein chahiye:

- **Demat Account:** Jaha aapke shares digital form mein store hote hain (jaise bank account mein paisa)
- **Trading Account:** Jisse aap buy/sell orders place karte ho

Simple bhasha mein: Demat account ek "digital locker" hai jahan aapke shares store hote hain. Trading account us locker mein shares daalne/nikalne (buy/sell) ke liye use hota hai. Dono aaj-kal ek saath hi khulte hain — Zerodha, Groww, Upstox jaise brokers se.

### Index Kya Hota Hai (Nifty, Sensex)

Index ek "summary number" hai jo batata hai overall market kaisa perform kar raha hai — bina har company ko individually dekhe.

- **Nifty 50** — NSE ke top 50 sabse bade companies ka average performance
- **Nifty 100** — NSE ke top 100 companies
- **Sensex** — BSE ke top 30 companies ka average performance

Agar news mein sunte ho "Market aaj 2% chadh gaya", matlab Nifty/Sensex 2% upar gaya — overall market ka mood positive tha.

---

## Part 2: Investing vs Trading

Share market mein paisa lagane ke do bade tareeke hain — dono ka goal alag hai, dono ka risk-level alag hai.

**Investing**
- Time period: Mahino-saalon tak hold karte hain
- Focus: Company ka business kaisa hai (fundamentals)
- Goal: Dheere-dheere wealth banana
- Risk: Apeksha-krit kam (lambe time mein)
- Beginner ke liye: Zyada safe starting point

**Trading**
- Time period: Din-hafton mein buy-sell ho jaata hai
- Focus: Price ka chart/movement kaisa hai (technicals)
- Goal: Short-term price movement se profit
- Risk: Zyada — daily decisions, fast losses possible
- Beginner ke liye: Practice aur discipline chahiye

Is document mein hum **Swing Trading** seekh rahe hain — jo trading ka ek beginner-friendly type hai (intraday jaisa fast-paced nahi).

---

## Part 3: Trading Ke Types

- **Intraday:** Same din buy aur sell. Sabse fast, sabse risky — screen pe constant dhyan chahiye.
- **Swing Trading:** Kuch din se 2-3 hafte. Relaxed pace, roz screen pe baithne ki zaroorat nahi.
- **Positional:** Hafto se mahino tak. Bada trend follow karna, patience chahiye.

Hum Swing Trading se shuru kar rahe hain kyunki ismein pressure kam hai aur seekhne ka time milta hai — perfect beginner starting point.

---

## Part 4: Chart Padhna Seekho (Technical Analysis Basics)

### Candlestick Chart

Har candle ek din (ya jo bhi timeframe ho) ka price movement dikhati hai — us din stock kahan khula (Open), kahan band hua (Close), sabse upar (High) aur sabse neeche (Low) kya gaya.

- **Green/White Candle:** Close, Open se zyada — matlab price upar gaya us din
- **Red/Black Candle:** Close, Open se kam — matlab price neeche gaya us din

### OHLC — Har Candle Ka Data

| Letter | Meaning | Kya hai |
|--------|---------|---------|
| **O** | Open | Jis price pe din shuru hua |
| **H** | High | Din ka sabse upar ka price |
| **L** | Low | Din ka sabse neeche ka price |
| **C** | Close | Jis price pe din band hua |

### Support aur Resistance

Ye do price levels hote hain jahan stock baar-baar "atakta" hai:

- **Support:** Wo level jahan stock girte-girte ruk jaata hai aur wapas upar bounce karta hai (jaise ek floor)
- **Resistance:** Wo level jahan stock chadhte-chadhte ruk jaata hai (jaise ek ceiling)

### Moving Average (EMA / SMA)

Moving Average pichle kuch dino ke average price ko ek smooth line ki tarah dikhata hai — isse trend ki direction clearly pata chalti hai.

| Type | Formula | Use |
|------|---------|-----|
| **SMA** | Simple average | Slow, less responsive |
| **EMA** | Weighted average (recent days ko zyada weight) | Fast, more responsive |

- **20 EMA** — pichle 20 din ka weighted average (short-term trend)
- **50 EMA** — pichle 50 din ka weighted average (medium-term trend)
- **20-week EMA** — pichle 20 hafte ka average (macro/long-term trend)

Jab short-term average (20 EMA), long-term average (50 EMA) se upar hota hai — matlab stock uptrend mein hai.

### Volume

Volume batata hai us din kitne shares trade hue. Zyada volume = zyada log us move mein participate kar rahe hain = move **"genuine"** hai. Kam volume ka breakout/move aksar **fake** nikalta hai.

---

## Part 5: Indicators Explained

### RSI — Relative Strength Index

RSI ek momentum indicator hai jo 0 se 100 ke beech rehta hai. Ye batata hai ki stock **overbought** hai ya **oversold**.

| RSI Value | Matlab |
|-----------|--------|
| 0–30 | Oversold (bahut zyada becha gaya, bounce possible) |
| 30–50 | Weak zone / recovery |
| 50–70 | Momentum zone (healthy uptrend) |
| 70–100 | Overbought (bahut zyada chada, correction possible) |

- Standard period: **RSI(14)** — pichle 14 dino ka data use karta hai
- **Wilder's Smoothing** se calculate hota hai — TradingView bhi yahi use karta hai

### MACD — Moving Average Convergence Divergence

MACD trend aur momentum dono dikhata hai. Teen components hain:

- **MACD Line** = 12-day EMA − 26-day EMA
- **Signal Line** = MACD line ka 9-day EMA
- **Histogram** = MACD Line − Signal Line

**Signal:**
- MACD line **Signal ke upar cross kare** → Bullish crossover (buy signal)
- MACD line **Signal ke neeche cross kare** → Bearish crossover (sell signal)

Histogram positive hona matlab momentum bullish direction mein hai.

### ATR — Average True Range

ATR batata hai ek stock average mein ek din mein kitna upar-neeche move karta hai — yani **volatility** measure karta hai.

- High ATR = volatile stock (zyada swing)
- Low ATR = stable stock (kam swing)
- **ATR-based stop-loss** = smarter, kyunki har stock ki apni volatility hoti hai

> **Example:** Agar ATR = Rs 15 aur aap Entry − 1.5×ATR pe stop-loss rakhte ho, toh stop = Entry − Rs 22.5. Ye stock ki natural movement ke hisaab se adjust hai.

### Supertrend Indicator

Supertrend ek trending indicator hai jo direct batata hai ki stock buy zone mein hai ya sell zone mein:

- **GREEN (neeche ki line)** = Bullish — stock buy zone mein
- **RED (upar ki line)** = Bearish — stock sell zone mein

Parameters: **Supertrend(10, 3)** — period 10, multiplier 3.0

Indian traders ke beech ye bahut popular hai kyunki ye clear visual signal deta hai.

### ADX — Average Directional Index

ADX batata hai trend **kitna strong** hai — direction nahi, sirf strength:

| ADX Value | Trend Strength |
|-----------|---------------|
| 0–20 | Weak / No trend (choppy market) |
| 20–40 | Moderate trend |
| 40–60 | Strong trend |
| 60+ | Very strong trend |

- ADX 20 se upar hona chahiye trade ke liye — warna price sirf noise mein hai

---

## Part 6: Risk Management (Sabse Important Part)

Trading mein zyadatar log isliye paisa khote hain kyunki wo risk management skip kar dete hain. Ye rules kabhi mat todna:

**1. Har trade mein sirf thoda risk lo**
Total capital ka **1-2%** se zyada kabhi ek trade mein risk mat lo. Agar capital Rs 1,00,000 hai, toh ek trade mein max Rs 1,000–2,000 ka hi risk lo.

**2. Stop-loss hamesha lagao**
Stop-loss ek price hai jahan pahunchte hi aap automatically exit ho jaate ho, taaki loss zyada na badhe. Bina stop-loss ke trading = gambling.

**3. Risk:Reward ratio check karo**
Kam se kam **1:2 ratio** rakho — matlab agar Rs 10 ka risk le rahe ho, toh target kam se kam Rs 20 ka profit hona chahiye. Isse agar 10 trades mein 4 bhi sahi gaye, tab bhi overall profit hoga.

**4. Two types of Stop-Loss:**
- **Fixed % SL:** Entry se 5% neeche (simple, but ignores volatility)
- **ATR-based SL:** Entry − 1.5×ATR (smarter — har stock ki volatility ke hisaab se adjust)

---

## Part 7: Strategy 1 — EMA Trend + Pullback

**File:** `strategies/ema_pullback.py`

### Concept

Uptrend mein chal rahe stock ka wait karo jab tak price thoda dip karke apni 20 EMA ke paas wapas aaye, phir bounce kare. Idea ye hai ki strong trend continue hoga, aur dip ek achha entry point deta hai — **"buy the dip in an uptrend"**.

### Rules

| Filter | Condition |
|--------|-----------|
| Universe | Nifty 50/100 liquid stocks |
| Trend | 20 EMA > 50 EMA (uptrend confirm) |
| Entry Trigger | Price 20 EMA ke paas aaye, phir bounce — aaj ka close, kal ki high se upar |
| Volume | Aaj ka volume > 10-day average volume |
| Stop-Loss | Entry se ~5% neeche |
| Target | Risk:Reward minimum 1:2 |

> **Example**
> Stock X, 20 EMA upar hai 50 EMA se — uptrend confirm.
> Price dip karke 20 EMA ke paas aaya, phir high volume ke saath bounce kiya — Entry signal.
> Entry = Rs 100 | Stop-loss = Rs 95 (5% neeche) | Risk = Rs 5/share
> Target = 100 + (5 × 2) = **Rs 110**
> Agar Rs 110 touch ho → profit book. Agar Rs 95 aaye → exit, loss accept karo.

> **Best Kab Kaam Karta Hai:** Strong trending market mein, jab overall Nifty bhi uptrend mein ho.

---

## Part 8: Strategy 2 — RSI Reversal

**File:** `strategies/rsi_reversal.py`

### Concept

RSI oversold zone (30 se neeche) se wapas 30 ke upar cross kare — ye reversal ka signal hai. Stock bahut zyada becha gaya tha, ab buyers wapas aa rahe hain.

### Rules

| Filter | Condition |
|--------|-----------|
| RSI Oversold | RSI(14) pehle 30 se neeche jaaye |
| RSI Cross | RSI wapas 30 ke upar cross kare (reversal confirm) |
| Price Confirm | Aaj ka close > kal ka close |
| Stop-Loss | Pichle 5 din ka lowest low |
| Target | Risk:Reward 1:2 |

> **Example**
> Stock Y ka RSI pichle kuch dino se 25 tha (oversold).
> Aaj RSI 31 ho gaya (30 ke upar cross) aur price bhi kal se zyada band hua.
> Entry = Rs 200 | Lowest low (5 din) = Rs 190 | Risk = Rs 10/share
> Target = 200 + (10 × 2) = **Rs 220**

> **Best Kab Kaam Karta Hai:** Choppy ya range-bound market mein jahan stocks oversold hokar bounce karte hain.

> **Caution:** "Falling knife" pakadne ka risk — stock oversold rehte hue bhi girta reh sakta hai. Overall Nifty downtrend mein ho toh is strategy ko avoid karo.

### Technical Note

RSI calculate karne ka standard = **Wilder's Smoothing** (TradingView aur charting platforms yahi use karte hain). Compare karte waqt hamesha same timeframe pe compare karo (daily vs daily).

---

## Part 9: Strategy 3 — Resistance Breakout

**File:** `strategies/breakout.py`

### Concept

Jab koi stock kaafi din tak ek range mein trade karta hai (consolidation), aur phir **resistance level todke high volume ke saath upar nikal jaata hai** — wo strong bullish signal hota hai. Naya trend shuru hone ka moment.

### Rules

| Filter | Condition |
|--------|-----------|
| Resistance Level | Pichle 20 din ka highest high |
| Breakout Trigger | Aaj ka close > resistance level |
| Volume Confirm | Breakout wale din volume > 1.5x–2x average volume |
| Stop-Loss | Breakout level ke thoda neeche |
| Target | Risk:Reward 1:2 ya 1:3 |

> **Example**
> Stock Z pichle 20 din se Rs 140–150 ke range mein tha. Resistance = Rs 150.
> Aaj stock Rs 153 pe close, volume average se double — Breakout confirm!
> Entry = Rs 153 | Stop-loss = Rs 147 | Risk = Rs 6/share
> Target = 153 + (6 × 2) = **Rs 165**

> **Best Kab Kaam Karta Hai:** Consolidation ke baad jab momentum build ho raha ho.

> **Caution:** Fake breakouts common hain — bina volume confirmation ke breakout pe trust mat karo. Price breakout ke baad wapas range mein aa sakta hai.

---

## Part 10: Strategy 4 — Multi-Confluence Momentum

**File:** `strategies/momentum_confluence.py`

### Concept

Ye ek **high-probability setup** hai jisme 5 independent indicators ek saath agree karte hain — tab hi trade lena. Jab itne saare signals ek direction mein point karte hain, trade ki reliability bahut badh jaati hai.

### Rules — 5 Filters (Sabka Pass Karna Zaroori)

| # | Filter | Condition |
|---|--------|-----------|
| 1 | **Macro Uptrend** | Close > 50-day EMA |
| 2 | **Fresh MACD Crossover** | MACD line aaj signal ke upar cross kare (entry timing) |
| 3 | **ADX Trend Strength** | ADX(14) > 20 (trend real hai, sirf noise nahi) |
| 4 | **RSI Momentum Zone** | RSI(14) between 50–70 (momentum building, overbought nahi) |
| 5 | **Volume Surge** | Volume > 1.2x 20-day average |

**Trade Levels:**
- **Entry:** Aaj ka closing price
- **Stop-Loss:** Pichle 5 din ka lowest low
- **Target:** Risk × 2.5 (1:2.5 risk-reward)

> **Example**
> Stock A: Close > EMA50 | MACD aaj cross kiya | ADX = 28 | RSI = 58 | Volume 1.4x average — sabhi 5 filters pass!
> Entry = Rs 500 | 5-day Low = Rs 480 | Risk = Rs 20/share
> Target = 500 + (20 × 2.5) = **Rs 550**

> **Best Kab Kaam Karta Hai:** Bull market mein jab momentum strong ho. ADX filter ensure karta hai ki hum sirf strong trends mein trade karo.

> **Ye Strategy Kyon Better Hai RSI Reversal se:**
> RSI Reversal counter-trend trade tha (market ke against). Ye strategy trend ke SAATH jaati hai — confluence = kam false signals.

---

## Part 11: Strategy 5 — Trend Surfer (7-Filter)

**File:** `strategies/trend_surfer.py`

### Concept

Ye **sabse selective aur high-conviction strategy** hai — 7 independent filters, sabka ek saath agree karna zaroori. Ek bhi filter fail kare toh trade nahi. Supertrend (Indian traders ka favourite) primary confirmation deta hai, aur ATR-based dynamic stop-loss market ki actual volatility ke hisaab se adjust hota hai.

**Motto:** *"Sirf best setup lo, koi bhi average trade nahi."*

### Rules — 7 Filters (Sabka Pass Karna Zaroori)

| # | Filter | Condition | Reason |
|---|--------|-----------|--------|
| 1 | **Weekly Uptrend** | Close > 20-week EMA | Macro picture bullish hona chahiye |
| 2 | **Daily EMA Structure** | Close > EMA20 AND Close > EMA50 | Daily structure solid |
| 3 | **Supertrend GREEN** | Supertrend(10,3) bullish | Trend currently intact |
| 4 | **RSI Sweet Spot** | RSI(14) between 45–70 | Momentum build ho raha, overbought nahi |
| 5 | **MACD Fresh Crossover** | MACD line signal ke upar (last 3 days mein) | Entry timing |
| 6 | **Volume Surge** | Volume > 1.2x 20-day average | Institutions aa rahe hain |
| 7 | **Bullish Candle** | Close > Open | Doji ya bearish candle pe entry nahi |

**Trade Levels (ATR-Based — Dynamic):**
- **Entry:** Aaj ka closing price
- **Stop-Loss:** Entry − 1.5 × ATR(14)
- **Target:** Entry + 3.0 × ATR(14)
- **Minimum R:R:** 1:1.8 (agar R:R 1.8 se kam ho toh bhi skip)

> **Example**
> Stock B: Sab 7 filters pass | ATR = Rs 20
> Entry = Rs 300
> Stop-Loss = 300 − (1.5 × 20) = **Rs 270**
> Target = 300 + (3.0 × 20) = **Rs 360**
> R:R = 30:60 = **1:2**

> **Best Kab Kaam Karta Hai:** Strong bull market mein jab multiple timeframes align hon.

> **Ye Kyon Best Strategy Hai:**
> - Counter-trend se completely bachi (sirf trend ke saath)
> - ATR-based SL = har stock ki volatility ke hisaab se adjust
> - 7 filters = bahut selective = jab signal aaye, high probability hai
> - MACD 3-day window = precise entry, stale signals nahi

---

## Part 12: Strategies Ka Comparison & Regime System

Market mein koi ek strategy har samay nahi chalti. Isi liye humne **Market Regime Filter** (Nifty 20 EMA / 50 EMA) integrate kiya hai taaki Bearish market mein galat longs na banayein.

| Strategy | Core Idea | Best Market / Regime | Main Risk | Selectivity |
|----------|-----------|----------------------|-----------|-------------|
| **⭐ Smart Pullback** | EMA Pullback + Volume + Strict 1:2 R:R | Bullish / Neutral | False breakdown | High (Best PF) |
| **EMA Pullback** | Uptrend mein 20 EMA dip se bounce | Bullish trending | Trend reverse ho jaaye | Medium |
| **Golden Cross** | 50 EMA crossing above 200 EMA | Early stage Bull market | Whipsaws / Lagging | Medium |
| **Trend Pullback** | Multi-EMA pullback with ATR SL | Bullish trending | Extended correction | High |
| **Trend Surfer** | 7 strict filters, ATR-based | Strong Bull market | Signals rare hain | Very High |
| **Precision 2R** | Support retest with strict 2R profit | Range & Bullish | Premature stop-out | High |
| **Volatility Squeeze** | Bollinger Band squeeze + Keltner breakout | Post-consolidation expansion | False breakout | High |
| **Regime RS Breakout** | Outperforming Nifty + Volume breakout | Only Bullish regime | Market correction | High |
| **Breakout** | Resistance level breakout with volume | Post-consolidation | Fake breakout / Bull trap | Medium |
| **Multi-Confluence** | 5 indicators agree (EMA, RSI, MACD, etc.) | Bullish market | Late entry possible | High |
| **RSI Reversal** | Oversold RSI (<30/35) bounce | Range-bound market | Falling knife in crash | Low |

> **Golden Rule of Trading:**  
> 1. **Bull Market (Nifty > 50 EMA & 20 EMA > 50 EMA):** Trend following aur Breakout strategies aggressive profit deti hain.  
> 2. **Bearish Market (Nifty < 50 EMA & 20 EMA < 50 EMA):** Long trades skip karo ya strictly cash me raho.  
> 3. **Risk Management First:** Har trade me max 1-2% capital risk karo, 1:2 Risk:Reward minimum rakho.

---

## Part 13: Zaroori Terms (Glossary)

| Term | Matlab |
|------|--------|
| **Entry** | Jis price pe stock kharida (next day open pe evaluate) |
| **Stop-Loss (SL)** | Jis price pe pahunchte hi exit — loss limit karne ke liye |
| **Target** | Jis price pe profit book karna hai |
| **Risk:Reward (R:R)** | Kitna risk lekar kitna reward — 1:2 matlab Rs 100 risk pe Rs 200 profit target |
| **Market Regime** | Nifty index ka overall state: Bullish, Neutral, ya Bearish |
| **Expectancy (%)** | Average percentage gain/loss expected per trade across backtest |
| **Profit Factor (PF)** | Total Gross Profit / Total Gross Loss (> 1.20 is solid, > 1.50 is exceptional) |
| **Uptrend / Downtrend** | Price ka overall direction (Higher Highs ya Lower Lows) |
| **Consolidation / Squeeze** | Stock ek narrow range mein aage-peeche move kare |
| **Breakout** | Price kisi important resistance ya range ko heavy volume se todkar nikal jaaye |
| **Pullback** | Uptrend mein thoda temporary dip jo support/EMA pe aakar rukta hai |
| **ATR** | Average True Range — volatility measure karta hai |
| **EMA** | Exponential Moving Average — recent prices ko zyada weight deta hai |
| **Paper Trading** | Real paisa lagaaye bina setup aur journal test karna |

---

## Part 14: Yaad Rakhne Wali Baatein

- Har trade mein risk total capital ka **1-2%** se zyada mat lo.
- **Stop-loss lagana non-negotiable hai** — bina SL ke entry = gambling.
- Trade journal maintain karo — entry/exit reason, result, aur seekh likhte jao.
- **Overall market (Nifty) ka regime check karo** — Bearish regime me long trades fail hone ke chances 70%+ hote hain.
- Naye strategy ko pehle `python backtest.py <strategy>` se verify karo aur kuch din paper trade karo.
- Ek din mein signal na aaye toh normal hai — **quality setups roz nahi bante, wait karna hi edge hai**.
- Patience ek superpower hai — trade force mat karo, system ke rules follow karo.

---

## Part 15: Humara Complete Trading System (Code Architecture)

Yeh notes sirf theory nahi — humne ek **professional modular swing trading screener + backtester** build kiya hai:

1. **Market Regime Check (`core/market_regime.py`):** Nifty 50 ka 20 EMA / 50 EMA trend monitor karta hai.
2. **Modular Strategy Engine (`strategies/`):** 11 plug-and-play strategies jisme se har ek apna signal, SL, target, aur regime requirement define karti hai.
3. **Data Layer (`core/ohlcv_data.py`):** Live NSE lists (Nifty 50, Nifty 100) aur clean yfinance historical OHLCV data provide karta hai.
4. **Walk-Forward Backtester (`backtest.py`):** Realistic next-day-open execution, slippage/cost model, max hold days, aur stop/target hit simulation karta hai.
5. **Regime Split Analysis (`regime_split.py`):** Backtested trades ko Bullish/Neutral/Bearish market ke according analyze karta hai.
6. **Live Screener + Google Sheets Sync (`run.py` & `integrations/gsheets.py`):** Daily screening signals ko `outputs/watchlist.csv` aur aapke connected Google Sheet par auto-append karta hai.

---

*Disclaimer: Ye educational notes hain, financial advice nahi. Market mein risk hota hai — apni research aur risk-tolerance ke hisaab se hi decide karo.*



## 📖 Complete Glossary & Short Forms (Full Forms & Meaning)

Agar aapko share market aur quantitative trading ke technical short forms me confusion ho, toh niche sabhi terms ki **Full Form** aur unka **Hindi + English** me simple meaning diya gaya hai:

### 1. Market & Price Action Terms (मार्केट और प्राइस टर्म्स)

| Short Form | Full Form | Simple Meaning (आसान मतलब) |
|---|---|---|
| **NSE** | National Stock Exchange | Bharat ka sabse bada stock exchange jahan shares trade hote hain. |
| **BSE** | Bombay Stock Exchange | Asia ka sabse purana stock exchange (Mumbai). |
| **NIFTY / NIFTY 50** | National Fifty | NSE ke top 50 blue-chip stocks ka benchmark index jo pure market ka trend batata hai. |
| **OHLCV** | Open, High, Low, Close, Volume | Ek candle ka pura data: Open (khula), High (sabse upar gaya), Low (sabse niche gaya), Close (band hua), Volume (kitne shares trade hue). |
| **LTP** | Last Traded Price | Stock ka abhi chal raha live price. |
| **CMP** | Current Market Price | Market me chal raha current price (LTP ke barabar). |
| **EOD** | End of Day | Market band hone ke baad (3:30 PM IST) ki completed daily candle. |
| **Tick Size** | Minimum Price Movement | NSE pe price minimum **₹0.05 (5 paise)** ke step me move karta hai (e.g. 100.00, 100.05, 100.10). |
| **IPO** | Initial Public Offering | Jab koi company pehli baar public se fund lene ke liye share market me aati hai. |

---

### 2. Technical Indicators (टेक्निकल इंडिकेटर्स)

| Short Form | Full Form | Simple Meaning (आसान मतलब) |
|---|---|---|
| **EMA** | Exponential Moving Average | Recent (taza) prices ko zyada weight dene wali moving average (e.g. 20 EMA, 50 EMA, 200 EMA). |
| **SMA** | Simple Moving Average | Sabhi dino ke price ko barabar weight dene wali average (e.g. 200-day SMA institutional benchmark). |
| **RSI** | Relative Strength Index | 0 se 100 tak ka momentum oscillator jo batata hai ki stock **Overbought (>70)** hai ya **Oversold (<30)**. |
| **TR** | True Range | Aaj ke High-Low ke sath kal ke Close se gap-up/gap-down ko mila kar nikala gaya real range. |
| **ATR** | Average True Range | Stock ki daily volatility (kitne rupaye upar-niche hota hai) batane wala indicator (Stop-Loss lagane ke kaam aata hai). |
| **MACD** | Moving Average Convergence Divergence | 12 EMA aur 26 EMA ka difference jo trend reversal aur momentum batata hai. |
| **ADX** | Average Directional Index | Trend kitna strong hai (Trend Strength) batata hai: **ADX > 20** = Strong trend, **ADX < 20** = Sideways/Choppy market. |
| **+DI / -DI** | Positive / Negative Directional Indicator | Bulls (+DI) vs Bears (-DI) me se kaun market ko dominate kar raha hai. |
| **BB** | Bollinger Bands | 20 SMA ke aas-paas 2 Standard Deviation ke bands jo volatility aur squeeze batate hain. |
| **KC** | Keltner Channels | EMA ke aas-paas ATR based volatility bands. |
| **RS** | Relative Strength | Stock Nifty ke comparison me kitna strong/outperform kar raha hai. |

---

### 3. Risk Management & Trading Execution (रिस्क मैनेजमेंट और ट्रेड्स)

| Short Form | Full Form | Simple Meaning (आसान मतलब) |
|---|---|---|
| **SL** | Stop Loss | Loss ko limit karne ka pre-decided price (agar price yahan gir jaye toh exit ho jao). |
| **TGT** | Target | Profit book karne ka pre-decided goal price. |
| **R:R / RR** | Risk to Reward Ratio | Kitne rupaye risk karke kitna kamane ka plan hai (e.g. 1:2 R:R yaani ₹1 ke risk pe ₹2 ka profit). |
| **2R** | 2 Times Initial Risk | Jab trade me profit aapke risk ka double (2x) ho jaye (e.g. Risk = ₹10, Target = ₹20). |
| **PnL / P&L** | Profit and Loss | Trade me hua munafa ya nuksan. |
| **R-Multiple** | PnL in terms of Risk | PnL / Initial Risk. (e.g. +2.0 R yaani risk se 2 guna profit hua, -1.0 R yaani stop loss hit hua). |
| **PF** | Profit Factor | Total Gross Profits / Total Gross Losses (PF > 1.5 yaani strategy profitable aur strong hai). |
| **Max DD** | Maximum Drawdown | Capital peak se le kar bottom tak kitna percent gira (strategy ka sabse bura daur). |
| **STT** | Securities Transaction Tax | Bharat sarkar dwara har buy/sell transaction pe lagne wala tax. |
| **RMS** | Risk Management System | Broker ka software jo order validation aur risk limits check karta hai. |

---

### 4. Technical & Code Terms (प्रोग्रामिंग और डेटा टर्म्स)

| Short Form | Full Form | Simple Meaning (आसान मतलब) |
|---|---|---|
| **CSV** | Comma-Separated Values | Excel jaisi tabular plain-text data file (jaise `watchlist.csv`). |
| **JSON** | JavaScript Object Notation | Data interchange format (jaise `client_secret.json`, API credentials). |
| **API** | Application Programming Interface | Do software ke beech baat karne ka bridge (jaise Yahoo Finance API ya Google Sheets API). |
| **TTL** | Time To Live | Cache kitni der tak valid rahega (e.g. 300 seconds TTL yaani 5 min tak purana downloaded data use hoga). |
| **CLI** | Command Line Interface | Terminal/PowerShell se commands run karne ka interface (e.g. `python run.py`). |
| **EWM** | Exponential Weighted Moving | Pandas ka function jisse EMA aur Wilder smoothing calculate hoti hai. |
