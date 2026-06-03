import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// Creates the React root element pointing to the HTML shell
const root = ReactDOM.createRoot(document.getElementById('root'));

// Mounts and renders your Feedback Intelligence dashboard
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);