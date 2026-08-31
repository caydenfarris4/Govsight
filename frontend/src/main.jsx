import React from 'react';
import ReactDOM from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import Chart from 'chart.js/auto';
import './styles/theme.css';
import App from './App.jsx';

// The embedded tools and vendor views reference Chart as a global
window.Chart = Chart;

// Charts speak the design system too: serif type, ink-tinted grid
Chart.defaults.font.family = '"Source Serif 4", Georgia, serif';
Chart.defaults.color = '#605d5d';
Chart.defaults.borderColor = 'rgba(32, 30, 29, 0.1)';

ReactDOM.createRoot(document.getElementById('root')).render(
  <HashRouter>
    <App />
  </HashRouter>
);
