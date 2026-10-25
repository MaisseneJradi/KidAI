/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

interface ImportMetaEnv {
  /** "false" pour utiliser le vrai backend FastAPI au lieu des mocks MSW. */
  readonly VITE_USE_MOCKS?: string;
}
