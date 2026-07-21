# Investment Optimizer - Rate Update Guide

## Overview
The Municipal Investment Optimizer displays investment rates for various safe municipal investment options. While Treasury rates come from live APIs, other rates are estimated based on current market conditions and should be updated monthly.

## Current Rates (Last Updated: October 2025)

| Investment Type | Current Rate | Update Frequency | Data Source |
|----------------|--------------|------------------|-------------|
| **US Treasury T-Bills** | 5.25-5.35% | Live API | US Treasury Fiscal Data API |
| **Vanguard VUSXX (MMF)** | 4.30% | Monthly | investor.vanguard.com/vusxx |
| **CDARS CD - 3 Month** | 4.00% | Monthly | Market comparison (CDARS ~0.25-0.50% below standard CDs) |
| **CDARS CD - 12 Month** | 4.15% | Monthly | Market comparison (CDARS ~0.25-0.50% below standard CDs) |
| **ICS Money Market** | 4.00% | Monthly | Contact IntraFi network banks |
| **State LGIP** | 5.00% | Monthly | National average from state treasuries |

---

## How to Update Rates (Monthly Maintenance)

### Step 1: Research Current Market Rates

**Vanguard VUSXX (Treasury Money Market Fund)**
1. Visit: https://investor.vanguard.com/investment-products/mutual-funds/profile/vusxx
2. Look for "7-Day SEC Yield"
3. Alternative sources:
   - Morningstar: https://www.morningstar.com/funds/xnas/vusxx/quote
   - Yahoo Finance: https://finance.yahoo.com/quote/VUSXX/

**CDARS (Certificate of Deposit)**
1. Check current standard CD rates at:
   - Bankrate: https://www.bankrate.com/banking/cds/current-cd-interest-rates/
   - NerdWallet: https://www.nerdwallet.com/best/banking/cd-rates
2. Subtract 0.25-0.50% from standard CD rates (CDARS typically lower due to network distribution)
3. 3-month CD example: If standard = 4.25%, CDARS ≈ 3.75-4.00%
4. 12-month CD example: If standard = 4.40%, CDARS ≈ 3.90-4.15%

**ICS (Insured Cash Sweep)**
1. No centralized rate feed available
2. Check sample banks:
   - Zeni: https://www.zeni.ai/blog/insured-cash-sweep
   - NerdWallet comparison: https://www.nerdwallet.com/article/small-business/insured-cash-sweep
3. Typical range: 2.50% - 4.05% (use midpoint ~3.75% or best available rate)

**State LGIP (Local Government Investment Pools)**
1. Check national averages:
   - S&P Global LGIP Report: Search "AAAm Local Government Investment Pool Trends"
   - National average typically 4.99-5.08% (use ~5.00%)
2. State-specific sources:
   - California LAIF: https://www.treasurer.ca.gov/pmia-laif/laif/index.asp
   - Texas TexPool: https://www.texasclass.com/
   - Washington: https://tre.wa.gov/investments-and-public-deposits/investments/local-government-investment-pool

### Step 2: Update the HTML File

**File Location:** `modules/navi/investment_optimizer_html.html`

**Find the OPPORTUNITIES array** (around line 539):
```javascript
// Investment opportunities data - Updated October 2025
const OPPORTUNITIES = [
```

**Update each rate** in the array:

```javascript
{
    id: 'mmf-vanguard',
    name: 'Vanguard Treasury Money Market Fund (VUSXX)',
    rate: 4.30,  // ← UPDATE THIS NUMBER
    source: '⚠️ ESTIMATED RATE (Oct 2025: 4.13-4.34%) - Verify at investor.vanguard.com/vusxx',
    // ↑ UPDATE THIS TEXT with current month and rate range
}
```

**Important fields to update:**
- `rate:` - The percentage (e.g., 4.30 for 4.30%)
- `source:` - Update the month and rate range in parentheses

### Step 3: Update the Documentation Comment

Change the header comment:
```javascript
// Investment opportunities data - Updated October 2025
```
to current month:
```javascript
// Investment opportunities data - Updated November 2025
```

### Step 4: Test the Changes

1. Restart the GovSight App workflow
2. Navigate to Navi → Investment Optimizer
3. Verify:
   - Rates display correctly on Investment Opportunities tab
   - Calculators work with new rates
   - Comparison chart shows updated values

---

## Rate Research Resources

### Quick Reference Links

**Money Market Funds:**
- Vanguard VUSXX: https://investor.vanguard.com/vusxx
- Schwab Treasury MMF: https://www.schwab.com/public/schwab/investing/accounts_products/investment/money_markets_funds
- Fidelity Government MMF: https://fundresearch.fidelity.com/mutual-funds/

**CD Rate Aggregators:**
- Bankrate CD rates: https://www.bankrate.com/banking/cds/current-cd-interest-rates/
- NerdWallet CD comparison: https://www.nerdwallet.com/best/banking/cd-rates
- FDIC National Rate Caps: https://www.fdic.gov/national-rates-and-rate-caps

**LGIP Resources:**
- GFOA LGIP Information: https://www.gfoa.org/materials/local-government-investment-pools
- MSRB LGIP Structure: https://www.msrb.org/LGIP-Investment-Pool-Structure

**IntraFi Network (CDARS/ICS):**
- IntraFi website: https://www.intrafi.com/
- Network bank list: https://www.intrafi.com/network-banks

### Market Context

**Federal Reserve Policy:**
- Current rates heavily influenced by Fed policy
- When Fed cuts rates, expect all rates to decline
- When Fed raises rates, expect all rates to increase
- Check Fed announcements: https://www.federalreserve.gov/

**Typical Rate Relationships:**
- Treasury Bills ≈ Federal Funds Rate (currently highest)
- State LGIPs ≈ Treasury Bills (close tracking)
- Vanguard MMF ≈ Treasury - 0.50% to 1.00%
- CDARS CDs ≈ Standard CDs - 0.25% to 0.50%
- ICS ≈ MMF or lower (bank-specific)

---

## Automation Ideas (Future Enhancement)

### Option 1: Web Scraping
Create a Python script to scrape Vanguard's VUSXX page monthly and auto-update the HTML.

### Option 2: Rate API Service
If budget allows, consider:
- Plaid API for Vanguard rates (~$0.75-$1.50/user/month)
- Financial data aggregators (Bloomberg, FactSet - enterprise pricing)

### Option 3: User Notifications
Add a "Last Updated" timestamp and remind users that rates are estimates requiring verification.

---

## Update Schedule

**Recommended:** Monthly (first business day of each month)

**Quick Update Process (15 minutes):**
1. Check Vanguard VUSXX (2 min)
2. Check Bankrate CD rates (2 min)
3. Review LGIP national average (3 min)
4. Update HTML file (5 min)
5. Test in browser (3 min)

**When to Update Immediately:**
- Major Federal Reserve rate changes (0.50%+ cut or raise)
- Significant market disruption
- User reports rates are outdated (>30 days old)

---

## Version History

| Date | Vanguard VUSXX | CDARS 3M | CDARS 12M | ICS | LGIP | Updated By |
|------|---------------|----------|-----------|-----|------|------------|
| Oct 2025 | 4.30% | 4.00% | 4.15% | 4.00% | 5.00% | Initial setup |

*Add new rows each time rates are updated for tracking purposes*

---

## Contact Information

**Questions about rate sources:**
- IntraFi Network: Contact your bank or visit www.intrafi.com
- State LGIPs: Contact your state treasury department
- Vanguard: investor.vanguard.com or 877-662-7447

**Technical questions:**
- Update the Investment Optimizer HTML file: `modules/navi/investment_optimizer_html.html`
- Review Git history for past rate changes
