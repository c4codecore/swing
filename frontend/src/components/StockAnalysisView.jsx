import React, { useEffect, useMemo, useState } from 'react';
import { ArrowDownRight, ArrowUpRight, RefreshCw, Search, ShieldAlert } from 'lucide-react';
import StockChart from './StockChart';

function price(value) {
  const number = Number(value);
  return value == null || !Number.isFinite(number)
    ? '—'
    : `₹${number.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
}

function percent(value) {
  return value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value) > 0 ? '+' : ''}${value}%`;
}

function toneText(tone) {
  return tone === 'good' ? 'Looks good' : tone === 'bad' ? 'Needs care' : tone === 'watch' ? 'Keep an eye' : 'For information';
}

function Metric({ label, value, tone = 'neutral' }) {
  return <article className={`stock-analysis-metric signal-${tone}`}><span>{label}</span><strong>{value ?? '—'}</strong><small className={`stock-signal-tag signal-${tone}`}>{toneText(tone)}</small></article>;
}

function technicalTone(metric, technical) {
  if (metric === 'trend') return /bullish|above ema/i.test(technical.trend || '') ? 'good' : /below ema/i.test(technical.trend || '') ? 'bad' : 'neutral';
  if (metric === 'ema') {
    if (technical.close == null || technical.ema20 == null || technical.ema50 == null) return 'neutral';
    if (technical.close > technical.ema20 && technical.ema20 > technical.ema50 && (technical.ema200 == null || technical.ema50 > technical.ema200)) return 'good';
    return technical.close < technical.ema50 ? 'bad' : 'watch';
  }
  if (metric === 'rsi') return technical.rsi14 == null ? 'neutral' : technical.rsi14 < 35 || technical.rsi14 > 70 ? 'bad' : technical.rsi14 >= 45 && technical.rsi14 <= 65 ? 'good' : 'watch';
  if (metric === 'adx') return technical.adx14 == null ? 'neutral' : technical.adx14 >= 25 ? 'good' : technical.adx14 < 15 ? 'watch' : 'neutral';
  if (metric === 'relative') return technical.mansfield_rs63 == null ? 'neutral' : technical.mansfield_rs63 > 0 ? 'good' : technical.mansfield_rs63 < 0 ? 'bad' : 'neutral';
  if (metric === 'returns') {
    if (technical.return20_pct == null || technical.return63_pct == null) return 'neutral';
    if (technical.return20_pct > 0 && technical.return63_pct > 0) return 'good';
    if (technical.return20_pct < 0 && technical.return63_pct < 0) return 'bad';
    return 'watch';
  }
  if (metric === 'atr') return technical.atr14_pct == null ? 'neutral' : technical.atr14_pct >= 5 ? 'bad' : technical.atr14_pct <= 2.5 ? 'good' : 'watch';
  if (metric === 'volume') return technical.volume_ratio20 == null ? 'neutral' : technical.volume_ratio20 >= 1.5 ? 'good' : technical.volume_ratio20 < 0.7 ? 'watch' : 'neutral';
  return 'neutral';
}

function fundamentalTone(label, value) {
  const number = Number(value);
  if (value == null || value === '' || !Number.isFinite(number)) return 'neutral';
  if (['Earnings for each share', 'Revenue growth', 'Earnings growth', 'Profit earned on shareholder money', 'Profit left from sales', 'Cash left after spending'].includes(label)) return number > 0 ? 'good' : number < 0 ? 'bad' : 'neutral';
  if (label === 'Debt compared with shareholder money') return number <= 100 ? 'good' : number > 200 ? 'bad' : 'watch';
  if (label === 'Money available for near-term bills') return number >= 1.5 ? 'good' : number < 1 ? 'bad' : 'watch';
  return 'neutral';
}

export default function StockAnalysisView() {
  const [stocks, setStocks] = useState([]);
  const [listMetadata, setListMetadata] = useState(null);
  const [query, setQuery] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState('');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const symbols = useMemo(() => stocks.map(stock => stock.symbol), [stocks]);

  useEffect(() => {
    let active = true;
    fetch('/api/symbols')
      .then(async response => {
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Stock list could not be loaded.');
        if (active) {
          setStocks(result.stocks || (result.symbols || []).map(symbol => ({ symbol, name: symbol })));
          setListMetadata(result);
        }
      })
      .catch(loadError => { if (active) setError(loadError.message || 'Stock list could not be loaded.'); });
    return () => { active = false; };
  }, []);

  const matches = useMemo(() => {
    const needle = query.trim().toUpperCase().replace(/\.NS$/, '');
    return needle ? stocks.filter(stock => stock.symbol.includes(needle) || stock.name.toUpperCase().includes(needle)) : stocks;
  }, [query, stocks]);

  const loadAnalysis = async rawSymbol => {
    const requested = rawSymbol.trim().toUpperCase().replace(/\.NS$/, '');
    const symbol = stocks.find(stock => stock.symbol === requested || stock.name.toUpperCase() === requested)?.symbol || requested;
    if (!symbol) { setError('Enter an NSE stock symbol or company name to begin.'); return; }
    if (!symbols.includes(symbol)) { setError('Choose a company or symbol from the NSE list.'); return; }
    setQuery(symbol);
    setSelectedSymbol(symbol);
    setLoading(true);
    setData(null);
    setError(null);
    try {
      const response = await fetch(`/api/stock/${encodeURIComponent(symbol)}/research`, { cache: 'no-store' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || `Analysis could not be loaded (${response.status}).`);
      setData(result);
    } catch (loadError) {
      setData(null);
      setError(loadError.message || 'Stock analysis could not be loaded.');
    } finally { setLoading(false); }
  };
  const analyze = event => {
    event?.preventDefault();
    return loadAnalysis(query);
  };

  const technical = data?.technical || {};
  const fundamentals = data?.fundamentals || {};
  const news = data?.news || {};
  const forecast = technical.forecast || {};
  const trendTone = technicalTone('trend', technical);
  const momentumTone = technicalTone('rsi', technical);
  const strengthTone = technicalTone('relative', technical);
  const returnTone = technicalTone('returns', technical);
  const volatilityTone = technicalTone('atr', technical);
  const momentumRead = technical.rsi14 == null ? 'Not enough price history'
    : technical.rsi14 >= 70 ? 'Price has risen quickly and may cool down'
      : technical.rsi14 <= 30 ? 'Recent prices have weakened sharply'
        : technical.rsi14 >= 55 ? 'Recent prices have mostly moved up'
          : technical.rsi14 <= 45 ? 'Recent prices have mostly moved down' : 'Recent prices are mixed';
  const strengthRead = technical.mansfield_rs63 == null ? 'Nifty comparison unavailable'
    : technical.mansfield_rs63 > 0 ? 'This share has done better than Nifty'
      : technical.mansfield_rs63 < 0 ? 'This share has done worse than Nifty' : 'About the same as Nifty';
  const volatilityRead = technical.atr14_pct == null ? 'Daily price movement unavailable'
    : technical.atr14_pct >= 5 ? 'Price often moves a lot in one day'
      : technical.atr14_pct >= 2.5 ? 'Price moves a moderate amount in one day' : 'Price usually moves less in one day';
  const fundamentalRead = fundamentals.status === 'unavailable' ? 'Company details are unavailable'
    : fundamentals.trailing_pe != null && fundamentals.return_on_equity != null
      ? `Price vs earnings: ${Number(fundamentals.trailing_pe).toFixed(1)} · profit on shareholder money: ${percent(fundamentals.return_on_equity * 100)}`
      : 'Some company details are unavailable';
  const simpleTrend = technical.trend === 'Bullish alignment' ? 'Price is above its short- and long-term averages'
    : technical.trend === 'Above EMA 50' ? 'Price is above its 50-day average'
      : technical.trend === 'Below EMA 50' ? 'Price is below its 50-day average' : technical.trend || 'Unavailable';
  const coreTones = [trendTone, technicalTone('ema', technical), strengthTone, returnTone].filter(tone => tone !== 'neutral');
  const supportiveCount = coreTones.filter(tone => tone === 'good').length;
  const cautionCount = coreTones.filter(tone => tone === 'bad').length;
  const verdict = coreTones.length < 2
    ? { tone: 'neutral', title: 'Jaankari abhi adhoori hai', text: 'Is stock par saaf read dene ke liye kaafi technical data nahi mila. Data update hone par phir review karein.' }
    : supportiveCount >= 3 && cautionCount === 0
      ? { tone: 'good', title: 'Rukh filhaal mazboot lag raha hai', text: 'Trend aur Nifty ke muqable ki strength support de rahe hain. Phir bhi khabar, valuation aur apna risk dekhkar hi faisla karein.' }
      : cautionCount >= 3 && supportiveCount === 0
        ? { tone: 'bad', title: 'Filhaal sambhal kar chalna behtar hai', text: 'Trend aur relative performance mein kamzori dikh rahi hai. Naya kadam lene se pehle behtari ki tasdeeq ka intezaar karein.' }
        : { tone: 'watch', title: 'Abhi ishare mile-jule hain', text: 'Kuch pehlu support karte hain, kuch savdhaani dikha rahe hain. Jaldi na karein; agle price action aur company updates par nazar rakhein.' };

  return <section className="module-page stock-analysis-page">
    <div className="module-heading">
        <div><div className="eyebrow subtle-eyebrow">MARKETVOICE · NSE RESEARCH</div><h1>Stock analysis</h1><p>See what recent prices, company details and news may tell you about a share.</p></div>
      {selectedSymbol && <button className="secondary-button" onClick={() => analyze()} disabled={loading}>{loading ? <RefreshCw size={14} className="spin" /> : <RefreshCw size={14} />}{loading ? 'Analyzing' : 'Refresh analysis'}</button>}
    </div>

    <form className="stock-analysis-search" onSubmit={analyze}>
      <label htmlFor="stock-analysis-symbol">Find a stock</label>
      <div className="stock-analysis-search-row">
        <div className="stock-analysis-input-wrap"><Search size={17} /><input id="stock-analysis-symbol" value={query} onChange={event => { setQuery(event.target.value); setError(null); }} placeholder="Search company or symbol, e.g. IRCTC" autoComplete="off" /></div>
        <button className="primary-button" type="submit" disabled={loading || !symbols.length}>{loading ? <RefreshCw size={15} className="spin" /> : <Search size={15} />}{loading ? 'Analyzing' : 'Analyze stock'}</button>
      </div>
      <small>Search by company name or stock code. {symbols.length ? `${symbols.length.toLocaleString('en-IN')} NSE-listed stocks` : 'Loading NSE stock list'} are available.</small>
      <div className="stock-symbol-list" aria-label="Supported NSE stock symbols">
        {matches.map(stock => <button key={stock.symbol} type="button" className={selectedSymbol === stock.symbol ? 'selected' : ''} onClick={() => loadAnalysis(stock.symbol)} disabled={loading} title={stock.name} aria-label={`${stock.symbol}, ${stock.name}`}>{stock.symbol}</button>)}
        {!matches.length && <span className="stock-symbol-empty">No supported symbols match that search.</span>}
      </div>
    </form>

    {error && <div className="portfolio-notice"><strong>{error}</strong></div>}
    {listMetadata?.list_status && listMetadata.list_status !== 'available' && <div className="portfolio-notice"><strong>{listMetadata.message || `NSE list status: ${listMetadata.list_status}`}</strong></div>}
    {loading && !data && <div className="empty-panel"><div className="loader-orb"><RefreshCw size={20} /></div><strong>Preparing stock analysis</strong><span>Loading daily prices, fundamentals and recent headlines…</span></div>}
    {!data && !loading && !error && <div className="empty-panel"><div className="empty-icon"><Search size={19} /></div><strong>Choose a stock to analyze</strong><span>Search by NSE ticker, then select Analyze stock.</span></div>}

    {data && <>
      <section className="stock-analysis-overview">
        <div className="stock-analysis-title"><span className="instrument-token large-token">{selectedSymbol.slice(0, 1)}</span><div><h2>{fundamentals.company_name || selectedSymbol}</h2><span>{selectedSymbol}{fundamentals.sector ? ` · ${fundamentals.sector}` : ''}{fundamentals.industry ? ` · ${fundamentals.industry}` : ''}</span></div></div>
        <div className="stock-analysis-price"><span>LATEST DAILY PRICE</span><strong>{price(technical.close)}</strong><small>As of {technical.as_of || 'unavailable'}</small></div>
      </section>

      <div className="stock-signal-legend"><span className="signal-good">Green · looks good</span><span className="signal-bad">Red · needs care</span><span className="signal-watch">Amber · keep an eye on it</span><span className="signal-neutral">Grey · extra information</span></div>
      <div className="stock-analysis-grid">
        <Metric label="Price direction" value={simpleTrend} tone={trendTone} />
        <Metric label="Recent price strength" value={technical.rsi14 != null ? technical.rsi14.toFixed(1) : '—'} tone={momentumTone} />
        <Metric label="How steady the trend is" value={technical.adx14 != null ? technical.adx14.toFixed(1) : '—'} tone={technicalTone('adx', technical)} />
        <Metric label="Price change vs Nifty" value={technical.mansfield_rs63 != null ? percent(technical.mansfield_rs63) : '—'} tone={strengthTone} />
        <Metric label="Price change over 1 / 3 months" value={technical.return20_pct != null && technical.return63_pct != null ? `${percent(technical.return20_pct)} / ${percent(technical.return63_pct)}` : '—'} tone={returnTone} />
        <Metric label="Usual daily price movement" value={technical.atr14_pct != null ? `${technical.atr14_pct}%` : '—'} tone={volatilityTone} />
        <Metric label="Trading today vs usual" value={technical.volume_ratio20 != null ? `${technical.volume_ratio20}×` : '—'} tone={technicalTone('volume', technical)} />
        <Metric label="Average price over 1 / 2 / 10 months" value={technical.ema20 != null ? `${price(technical.ema20)} / ${price(technical.ema50)} / ${price(technical.ema200)}` : '—'} tone={technicalTone('ema', technical)} />
      </div>

      <section className="stock-analysis-panel">
        <div className="stock-analysis-section-heading"><div><div className="eyebrow subtle-eyebrow">SIMPLE SUMMARY</div><h2>What recent prices suggest</h2></div><span>Helpful clues, not instructions to buy or sell</span></div>
        <div className="stock-analysis-readout-grid">
          <article className={`signal-${trendTone}`}><span>Price direction</span><strong>{simpleTrend}</strong><small>Compared with recent average prices</small></article>
          <article className={`signal-${momentumTone}`}><span>Recent price strength</span><strong>{momentumRead.replace(/RSI is /, 'Price is ')}</strong><small>Shows whether the recent move is strong or stretched</small></article>
          <article className={`signal-${strengthTone}`}><span>Price change vs Nifty</span><strong>{strengthRead.replace('Outperforming', 'Doing better than').replace('Underperforming', 'Doing worse than')}</strong><small>Compared with the Nifty over about 3 months</small></article>
          <article className={`signal-${volatilityTone}`}><span>Usual daily price movement</span><strong>{volatilityRead.replace('Volatility data', 'Price movement data').replace('ATR', 'daily range')}</strong><small>How much the share price often moves in a day</small></article>
          <article className={`signal-${fundamentals.status === 'unavailable' ? 'neutral' : 'watch'}`}><span>Company details</span><strong>{fundamentalRead}</strong><small>Some figures may be delayed or missing</small></article>
        </div>
      </section>

      <section className="stock-analysis-panel">
        <div className="stock-analysis-section-heading"><div><div className="eyebrow subtle-eyebrow">PRICE HISTORY</div><h2>{selectedSymbol} chart</h2></div><span>Daily prices, recent averages and price strength</span></div>
        <StockChart symbol={selectedSymbol} />
      </section>

      <section className="stock-analysis-panel forecast-panel">
        <div className="stock-analysis-section-heading"><div><div className="eyebrow subtle-eyebrow">PAST PRICE EXAMPLE</div><h2>Possible future price range</h2></div><span>{forecast.status === 'available' ? `Based on ${forecast.observations} past daily changes` : 'Unavailable'}</span></div>
        {forecast.status === 'available' ? <>
          <div className="forecast-scenario-grid">{forecast.scenarios.map(scenario => {
            const up = scenario.base_return_pct >= 0;
            return <article className="forecast-scenario" key={scenario.sessions}>
              <span>{scenario.label}</span><div className={`forecast-base ${up ? 'positive' : 'negative'}`}>{up ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}<strong>{price(scenario.base_price)}</strong><small>{percent(scenario.base_return_pct)} if past pattern repeats</small></div>
              <div className="forecast-range"><div><span>Lower example</span><strong>{price(scenario.low_price)}</strong><small>{percent(scenario.low_return_pct)}</small></div><i /><div><span>Upper example</span><strong>{price(scenario.high_price)}</strong><small>{percent(scenario.high_return_pct)}</small></div></div>
            </article>;
          })}</div>
          <p className="forecast-method"><ShieldAlert size={15} /> These examples use past daily price changes to show what might happen if a similar pattern repeats. Prices can move far outside these ranges; this is not a reliable prediction.</p>
        </> : <p className="research-empty">There is not enough recent history to calculate scenario ranges.</p>}
      </section>

      <section className="stock-analysis-panel">
          <div className="stock-analysis-section-heading"><div><div className="eyebrow subtle-eyebrow">COMPANY SNAPSHOT</div><h2>Company details</h2></div><span>{fundamentals.status || 'Unavailable'} · {fundamentals.source || 'provider data'}</span></div>
        {(fundamentals.sector || fundamentals.industry) && <p className="stock-analysis-muted">{[fundamentals.sector, fundamentals.industry].filter(Boolean).join(' · ')}</p>}
        <div className="stock-analysis-fundamentals">
          {[
            ['Company size (market value)', fundamentals.market_cap, 'money'], ['Share price vs past earnings', fundamentals.trailing_pe, 'number'], ['Share price vs expected earnings', fundamentals.forward_pe, 'number'],
            ['Share price vs company assets', fundamentals.price_to_book, 'number'], ['Earnings for each share', fundamentals.eps_ttm, 'money'], ['Yearly dividend paid', fundamentals.dividend_yield == null ? null : `${(fundamentals.dividend_yield * 100).toFixed(2)}%`, 'text'],
            ['Revenue growth', fundamentals.revenue_growth == null ? null : percent(fundamentals.revenue_growth * 100), 'text', fundamentals.revenue_growth * 100], ['Earnings growth', fundamentals.earnings_growth == null ? null : percent(fundamentals.earnings_growth * 100), 'text', fundamentals.earnings_growth * 100],
            ['Profit earned on shareholder money', fundamentals.return_on_equity == null ? null : percent(fundamentals.return_on_equity * 100), 'text', fundamentals.return_on_equity * 100], ['Profit left from sales', fundamentals.profit_margin == null ? null : percent(fundamentals.profit_margin * 100), 'text', fundamentals.profit_margin * 100],
            ['Debt compared with shareholder money', fundamentals.debt_to_equity, 'number'], ['Money available for near-term bills', fundamentals.current_ratio, 'number'], ['Cash left after spending', fundamentals.free_cash_flow, 'money'], ['Price movement compared with market', fundamentals.beta, 'number'],
          ].map(([label, value, kind, rawValue]) => { const tone = fundamentalTone(label, rawValue ?? value); return <div className={`stock-analysis-fundamental signal-${tone}`} key={label}><span>{label}</span><strong>{value == null ? '—' : kind === 'money' ? price(value) : kind === 'number' ? Number(value).toLocaleString('en-IN', { maximumFractionDigits: 2 }) : value}</strong><small className={`stock-signal-tag signal-${tone}`}>{toneText(tone)}</small></div>; })}
        </div>
        {fundamentals.error && <p className="research-empty">{fundamentals.error}</p>}
      </section>

      <section className="stock-analysis-panel">
        <div className="stock-analysis-section-heading"><div><div className="eyebrow subtle-eyebrow">RECENT HEADLINES</div><h2>News and event context</h2></div><span>{news.status || 'Unavailable'} · {news.source || 'news provider'}</span></div>
        <p className="stock-analysis-muted">Headlines are a limited screen and may miss context. Review company announcements and exchange filings directly.</p>
        {news.event_risk && <div className="research-risk">Potential event-risk wording found. Review the stories and filings before making a decision.</div>}
        {news.headlines?.length ? <ul className="research-news-list">{news.headlines.map((item, index) => <li key={`${item.title}-${index}`}><div>{item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a> : item.title}</div><small>{[item.source, item.published_at ? new Date(item.published_at).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }) : null].filter(Boolean).join(' · ')}</small></li>)}</ul> : <p className="research-empty">{news.status === 'unavailable' ? 'News could not be fetched. Check current announcements manually.' : 'No recent headlines were returned.'}</p>}
      </section>
      <p className="stock-analysis-disclaimer">For learning and research, not personal financial advice. Company figures and news may be delayed or incomplete. Any future price range is only an example from past prices; actual prices can be very different.</p>
      <section className={`stock-deshi-verdict signal-${verdict.tone}`}>
        <div><span>DESI VERDICT · RULE-BASED SUMMARY</span><h2>{verdict.title}</h2><p>{verdict.text}</p></div>
        <small>{supportiveCount} signs look positive · {cautionCount} signs need care</small>
      </section>
    </>}
  </section>;
}
