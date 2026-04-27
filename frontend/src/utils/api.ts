import axios from 'axios'
import toast from 'react-hot-toast'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120_000,
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Request failed'
    toast.error(msg)
    return Promise.reject(err)
  }
)

export default api

// ---- Anonymisation ----

export const anonymiseText = (text: string, documentId?: string) =>
  api.post('/anonymise/text', { text, document_id: documentId }).then(r => r.data)

export const anonymiseDocument = (file: File, returnTokens = false) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('return_tokens', String(returnTokens))
  return api.post('/anonymise/document', fd).then(r => r.data)
}

export const anonymiseStructured = (file: File, sensitiveColumns: string) => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('sensitive_columns', sensitiveColumns)
  return api.post('/anonymise/structured', fd).then(r => r.data)
}

// ---- Summarisation ----

export const summariseText = (text: string, documentType: string, applicationType = 'default') =>
  api.post('/summarise/text', { text, document_type: documentType, application_type: applicationType }).then(r => r.data)

export const summariseDocument = (file: File, documentType: string, applicationType = 'default') => {
  const fd = new FormData()
  fd.append('file', file)
  fd.append('document_type', documentType)
  fd.append('application_type', applicationType)
  return api.post('/summarise/document', fd).then(r => r.data)
}

export const summariseAudio = (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  return api.post('/summarise/audio', fd).then(r => r.data)
}

// ---- Completeness ----

export const checkCompleteness = (text: string, documentType: string, documentId = 'doc_001') =>
  api.post('/completeness/check', { text, document_type: documentType, document_id: documentId }).then(r => r.data)

export const compareDocuments = (textA: string, textB: string, docAId = 'version_A', docBId = 'version_B') =>
  api.post('/completeness/compare', { text_a: textA, text_b: textB, doc_a_id: docAId, doc_b_id: docBId }).then(r => r.data)

// ---- Classification ----

export const classifySeverity = (text: string, caseId = 'unknown') =>
  api.post('/classify/severity', { text, case_id: caseId }).then(r => r.data)

export const checkDuplicate = (text: string, caseId: string, registerCase = true) =>
  api.post('/classify/duplicate', { text, case_id: caseId, register_case: registerCase }).then(r => r.data)

export const buildPriorityQueue = (cases: object[]) =>
  api.post('/classify/queue', { cases }).then(r => r.data)
