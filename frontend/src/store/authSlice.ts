import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { authApi } from "../api/finsight";
import { apiErrorMessage } from "../lib/errors";
import type { User } from "../types";

interface AuthState {
  user: User | null;
  status: "idle" | "loading" | "authenticated" | "anonymous";
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  status: "idle",
  error: null,
};

export const bootstrapAuth = createAsyncThunk("auth/bootstrap", async () => {
  const token = localStorage.getItem("finsight_access");
  if (!token) return null;
  return authApi.me();
});

export const login = createAsyncThunk(
  "auth/login",
  async (payload: { email: string; password: string }, { rejectWithValue }) => {
    try {
      const tokens = await authApi.login(payload);
      localStorage.setItem("finsight_access", tokens.access_token);
      localStorage.setItem("finsight_refresh", tokens.refresh_token);
      return authApi.me();
    } catch (err: unknown) {
      return rejectWithValue(apiErrorMessage(err, "Login failed"));
    }
  },
);

export const register = createAsyncThunk(
  "auth/register",
  async (
    payload: { email: string; full_name: string; password: string },
    { rejectWithValue, dispatch },
  ) => {
    try {
      await authApi.register(payload);
      return dispatch(login({ email: payload.email, password: payload.password })).unwrap();
    } catch (err: unknown) {
      return rejectWithValue(apiErrorMessage(err, "Registration failed"));
    }
  },
);

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    logout(state) {
      localStorage.removeItem("finsight_access");
      localStorage.removeItem("finsight_refresh");
      state.user = null;
      state.status = "anonymous";
      state.error = null;
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(bootstrapAuth.pending, (state) => {
        state.status = "loading";
      })
      .addCase(bootstrapAuth.fulfilled, (state, action) => {
        state.user = action.payload;
        state.status = action.payload ? "authenticated" : "anonymous";
      })
      .addCase(bootstrapAuth.rejected, (state) => {
        state.user = null;
        state.status = "anonymous";
      })
      .addCase(login.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.user = action.payload;
        state.status = "authenticated";
      })
      .addCase(login.rejected, (state, action) => {
        state.status = "anonymous";
        state.error = String(action.payload || "Login failed");
      })
      .addCase(register.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(register.fulfilled, (state, action) => {
        state.user = action.payload;
        state.status = "authenticated";
      })
      .addCase(register.rejected, (state, action) => {
        state.status = "anonymous";
        state.error = String(action.payload || "Registration failed");
      });
  },
});

export const { logout, clearError } = authSlice.actions;
export default authSlice.reducer;
