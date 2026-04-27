import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import './index.css'

import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import AnonymisationPage from '@/pages/Anonymisation'
import SummarisationPage from '@/pages/Summarisation'
import CompletenessPage from '@/pages/Completeness'
import ClassificationPage from '@/pages/Classification'
import QueuePage from '@/pages/Queue'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="anonymise" element={<AnonymisationPage />} />
          <Route path="summarise" element={<SummarisationPage />} />
          <Route path="completeness" element={<CompletenessPage />} />
          <Route path="classify" element={<ClassificationPage />} />
          <Route path="queue" element={<QueuePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
    <Toaster
      position="bottom-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: '#1A1714',
          color: '#F4F2EE',
          fontSize: '13px',
          fontFamily: 'IBM Plex Sans, sans-serif',
          borderRadius: '5px',
          padding: '10px 14px',
        },
      }}
    />
  </React.StrictMode>
)
