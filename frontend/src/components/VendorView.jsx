import React, { useEffect, useRef } from 'react';
import { getBundle } from '../api.js';
// Side-effect imports: these attach DEMO_VIEWS / BI_SANDBOX to window
import '../vendor/demo_views.js';
import '../vendor/bi_sandbox.js';

// Renders one of the vendor data views, fed by the live platform bundle
export default function VendorView({ view }) {
  const ref = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const el = ref.current;
    el.innerHTML = '<div style="padding:30px;color:#5b6b7a">Loading data…</div>';
    getBundle()
      .then((bundle) => {
        if (cancelled) return;
        window.DEMO_VIEWS.setData(bundle);
        window.DEMO_VIEWS.render(view, el);
      })
      .catch((err) => {
        if (!cancelled) {
          el.innerHTML =
            `<div style="padding:30px;color:#a4271c">Could not load data: ${err.message}</div>`;
        }
      });
    return () => { cancelled = true; };
  }, [view]);

  return (
    <div style={{ padding: 20, maxWidth: 1240, margin: '0 auto', width: '100%' }}
         ref={ref} />
  );
}
