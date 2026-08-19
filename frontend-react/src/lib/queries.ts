// How a screen asks the server for something.
//
// Three hooks and one mutation helper, all on top of @tanstack/react-query, so
// caching, de-duplication, loading state and error state are decided once here
// instead of thirteen times in thirteen screens. A screen imports from this
// file and from lib/frappe.ts only for types; it never calls fetch.
//
//   const jobs = useList<JobRow>({ doctype: "Job", fields: [...] });
//   const owed = useMethod<Overdue>("auraos.api.overdue_milestones");
//   const log  = useMethodMutation("auraos.api.log_job_expense", {
//     invalidate: [listsOf("Job Expense")],
//   });
//
// Render the result with <QueryState> from components/aura/states.tsx rather
// than reading isPending / isError by hand, so every screen's loading and empty
// states look alike.

import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryKey,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";

import { callMethod, getDoc, getList, type FrappeError, type ListQuery } from "./frappe";

/**
 * Cache keys. Prefixes are stable and public: anything under ["list", "Job"] is
 * a Job list, so a mutation can invalidate every one of them without knowing
 * which screens exist.
 */
export function listsOf(doctype: string): QueryKey {
  return ["list", doctype];
}

export function resultOf(method: string): QueryKey {
  return ["method", method];
}

/**
 * The key useDoc reads under. A write that changes one document invalidates
 * this rather than the whole list: the detail screen is the only reader, and a
 * list refetch would not reach it.
 */
export function docOf(doctype: string, name: string): QueryKey {
  return ["doc", doctype, name];
}

function methodKey(method: string, args: unknown): QueryKey {
  return ["method", method, args ?? null];
}

function listKey(query: ListQuery): QueryKey {
  return ["list", query.doctype, query];
}

/** Options a screen is allowed to pass through. Everything else is the layer's. */
export type QueryOptions = {
  /** Skip the request until a dependency exists, e.g. a selected job. */
  enabled?: boolean;
  /** Milliseconds the answer stays fresh. Defaults to the client's 30s. */
  staleTime?: number;
  /** Off for a probe whose failure is itself the answer. */
  retry?: boolean;
};

/**
 * Call a whitelisted method. `args` is part of the cache key, so two screens
 * asking the same endpoint the same question share one request.
 */
export function useMethod<T>(
  method: string,
  args?: Record<string, unknown>,
  options: QueryOptions = {},
): UseQueryResult<T, FrappeError> {
  return useQuery<T, FrappeError>({
    queryKey: methodKey(method, args),
    queryFn: () => callMethod<T>(method, args ?? {}),
    ...options,
  });
}

/** Read a doctype list, with filters, fields, ordering and a limit. */
export function useList<T>(
  query: ListQuery,
  options: QueryOptions = {},
): UseQueryResult<T[], FrappeError> {
  return useQuery<T[], FrappeError>({
    queryKey: listKey(query),
    queryFn: () => getList<T>(query),
    ...options,
  });
}

/** Read one document by name. */
export function useDoc<T>(
  doctype: string,
  name: string | undefined,
  options: QueryOptions = {},
): UseQueryResult<T, FrappeError> {
  return useQuery<T, FrappeError>({
    queryKey: ["doc", doctype, name ?? null],
    queryFn: () => getDoc<T>(doctype, name as string),
    enabled: Boolean(name) && options.enabled !== false,
    ...options,
  });
}

/**
 * A mutating call. Every request this app makes carries the CSRF token, so
 * there is nothing extra to do here beyond saying what the write invalidates.
 *
 * Use `mutate(args)` and read `mutation.error` for the failure. Do not `await
 * mutateAsync` without a catch: that is the one way to produce the unhandled
 * rejection this layer exists to prevent.
 */
export function useMethodMutation<TResult, TArgs extends Record<string, unknown>>(
  method: string,
  options: {
    /** Cache keys to refetch on success. Prefixes work: `listsOf("Job")`. */
    invalidate?: QueryKey[];
    onSuccess?: (result: TResult, args: TArgs) => void;
  } = {},
): UseMutationResult<TResult, FrappeError, TArgs> {
  const client = useQueryClient();

  return useMutation<TResult, FrappeError, TArgs>({
    mutationFn: (args: TArgs) => callMethod<TResult>(method, args),
    onSuccess: (result, args) => {
      for (const key of options.invalidate ?? []) {
        void client.invalidateQueries({ queryKey: key });
      }
      options.onSuccess?.(result, args);
    },
  });
}
