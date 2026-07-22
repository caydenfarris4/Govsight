import React, { useEffect, useRef } from 'react';
import { mountInvestmentOptimizer } from '../tools/investmentOptimizer.js';

export default function InvestmentOptimizer() {
  const ref = useRef(null);
  useEffect(() => {
    mountInvestmentOptimizer(ref.current);
    const el = ref.current;
    return () => { el.innerHTML = ''; };
  }, []);
  return <div ref={ref} style={{ width: '100%' }} />;
}
