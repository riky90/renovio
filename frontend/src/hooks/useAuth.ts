import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getMe,
  postLogin,
  postLogout,
  postRegistrazione,
  type LoginInput,
  type RegistrazioneInput,
  type UserOut,
} from "@/api/auth";

export const AUTH_QUERY_KEY = ["me"] as const;

/**
 * Sessione corrente (useQuery su GET /auth/me, 401 -> null) + mutazioni
 * login/registrazione/logout. Tutte le mutazioni invalidano ["me"] al
 * successo così l'header/AccountMenu si aggiorna ovunque sia montato.
 */
export function useAuth() {
  const queryClient = useQueryClient();

  const meQuery = useQuery<UserOut | null>({
    queryKey: AUTH_QUERY_KEY,
    queryFn: getMe,
  });

  const registrazioneMutation = useMutation({
    mutationFn: (input: RegistrazioneInput) => postRegistrazione(input),
    onSuccess: (user) => {
      queryClient.setQueryData(AUTH_QUERY_KEY, user);
      void queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEY });
    },
  });

  const loginMutation = useMutation({
    mutationFn: (input: LoginInput) => postLogin(input),
    onSuccess: (user) => {
      queryClient.setQueryData(AUTH_QUERY_KEY, user);
      void queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEY });
    },
  });

  const logoutMutation = useMutation({
    mutationFn: () => postLogout(),
    onSuccess: () => {
      queryClient.setQueryData(AUTH_QUERY_KEY, null);
      void queryClient.invalidateQueries({ queryKey: AUTH_QUERY_KEY });
    },
  });

  return {
    user: meQuery.data ?? null,
    isLoading: meQuery.isLoading,
    registrazione: registrazioneMutation,
    login: loginMutation,
    logout: logoutMutation,
  };
}
