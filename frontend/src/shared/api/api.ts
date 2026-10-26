import { authApi } from "./endpoints/auth";
import { learningApi } from "./endpoints/learning";
import { vocabularyApi } from "./endpoints/vocabulary";
import { testsApi } from "./endpoints/tests";
import { listeningApi } from "./endpoints/listening";
import { writingApi } from "./endpoints/writing";
import { speakingApi } from "./endpoints/speaking";
import { analyticsApi } from "./endpoints/analytics";
import { historyApi } from "./endpoints/history";

export { mediaUrl } from "./config";
export { NetworkError, isNetworkError } from "./errors";
export { fetchAuthenticatedMedia, warmUpServer } from "./http";
export { getStoredAuthToken, getStoredUsername, storeAuth, clearStoredAuth } from "./token";
export * from "./types";

export const api = {
  ...authApi,
  ...learningApi,
  ...vocabularyApi,
  ...testsApi,
  ...listeningApi,
  ...writingApi,
  ...speakingApi,
  ...analyticsApi,
  ...historyApi,
};
export { useWarmUp } from "./useWarmUp";
