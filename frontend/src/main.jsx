import React from 'react';
import ReactDOM from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import Chart from 'chart.js/auto';
import App from './App.jsx';

// The embedded tools and vendor views reference Chart as a global
window.Chart = Chart;

ReactDOM.createRoot(document.getElementById('root')).render(
  <HashRouter>
    <App />
  </HashRouter>
);
