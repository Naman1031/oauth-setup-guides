/// <reference types="vite/client" />

// Types for the environment variables our code reads via import.meta.env.
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
