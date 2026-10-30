const indianNumber = new Intl.NumberFormat('en-IN', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatNumber(value, fallback = '—') {
  const number = Number(value);
  return value == null || value === '' || !Number.isFinite(number)
    ? fallback
    : indianNumber.format(number);
}

export function formatINR(value, fallback = '—') {
  const number = Number(value);
  return value == null || value === '' || !Number.isFinite(number)
    ? fallback
    : `₹${indianNumber.format(number)}`;
}

export function formatPercent(value, { signed = false, fraction = false, fallback = '—' } = {}) {
  const number = Number(value);
  if (value == null || value === '' || !Number.isFinite(number)) return fallback;
  const percentage = fraction ? number * 100 : number;
  return `${signed && percentage > 0 ? '+' : ''}${percentage.toFixed(2)}%`;
}
