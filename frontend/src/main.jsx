import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import 'vazirmatn/Vazirmatn-font-face.css'
import 'react-multi-date-picker/styles/colors/green.css'
import 'react-multi-date-picker/styles/layouts/mobile.css'
import './theme.css'
import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
