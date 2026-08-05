import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("finsight_access");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = localStorage.getItem("finsight_refresh");
      if (refresh) {
        try {
          const { data } = await axios.post(
            `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/auth/refresh`,
            { refresh_token: refresh },
          );
          localStorage.setItem("finsight_access", data.access_token);
          localStorage.setItem("finsight_refresh", data.refresh_token);
          original.headers.Authorization = `Bearer ${data.access_token}`;
          return api(original);
        } catch {
          localStorage.removeItem("finsight_access");
          localStorage.removeItem("finsight_refresh");
        }
      }
    }
    return Promise.reject(error);
  },
);

export default api;
