const apiBase = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

export type Page<T> = { items: T[]; skip: number; limit: number; total: number };
export type ApiProduct = {
  id: number;
  sku: string;
  name: string;
  category: string;
  price: string | number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};
export type ApiStore = {
  id: number;
  code: string;
  name: string;
  location: string;
  is_active: boolean;
};
export type ApiInventory = {
  id: number;
  product: { id: number; sku: string; name: string; category: string; price: string | number };
  store: { id: number; code: string; name: string; location: string };
  quantity: number;
  reorder_level: number;
  status: "out_of_stock" | "below_reorder" | "healthy";
  updated_at: string;
};
export type ApiActivity = {
  id: number;
  movement_id: number | null;
  product_id: number | null;
  store_id: number | null;
  event_type: string;
  product_name: string;
  sku: string | null;
  store_name: string;
  quantity_delta: number;
  note: string;
  is_batch: boolean;
  occurred_at: string;
};
export type ApiSummary = {
  total_units: number;
  product_count: number;
  store_count: number;
  category_count: number;
  healthy_balances: number;
  low_balances: number;
  out_of_stock_balances: number;
  total_balances: number;
  recent_activity: ApiActivity[];
};
export type ApiReplenishment = {
  inventory_id: number;
  product_id: number;
  sku: string;
  product_name: string;
  store_id: number;
  store_code: string;
  store_name: string;
  quantity: number;
  reorder_level: number;
  deficit: number;
  suggested_quantity: number;
  priority: number;
};
export type ImportPreview = {
  file_name: string;
  policy: "all_or_nothing";
  total_rows: number;
  accepted_count: number;
  rejected_count: number;
  can_commit: boolean;
  accepted_rows: {
    row_number: number;
    sku: string;
    product_name: string;
    store_code: string;
    store_name: string;
    old_quantity: number;
    new_quantity: number;
    reorder_level: number;
  }[];
  rejected_rows: { row_number: number; values: Record<string, string>; errors: string[] }[];
};
export type ImportResult = ImportPreview & {
  imported_count: number;
  changed_units: number;
  history_entries: number;
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && typeof init.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response: Response;
  try {
    response = await fetch(`${apiBase}${path}`, { ...init, headers });
  } catch {
    throw new Error("StockFlow API is unreachable. Check that the backend is running.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = body?.error?.message ?? body?.detail ?? `Request failed (${response.status}).`;
    const details = body?.error?.details;
    throw new Error(
      Array.isArray(details) && details.length
        ? `${message} ${details.map((detail: { message?: string }) => detail.message).filter(Boolean).join(" ")}`
        : message,
    );
  }
  return body as T;
}

async function requestAll<T>(path: string): Promise<Page<T>> {
  const items: T[] = [];
  let total = 0;
  do {
    const separator = path.includes("?") ? "&" : "?";
    const page = await request<Page<T>>(`${path}${separator}skip=${items.length}&limit=200`);
    items.push(...page.items);
    total = page.total;
    if (!page.items.length) break;
  } while (items.length < total);
  return { items, skip: 0, limit: 200, total };
}

export const api = {
  products: () => requestAll<ApiProduct>("/products"),
  product: (id: number) => request<ApiProduct>(`/products/${id}`),
  createProduct: (body: { sku: string; name: string; category: string; price: number }) =>
    request<ApiProduct>("/products", { method: "POST", body: JSON.stringify(body) }),
  updateProduct: (id: number, body: Partial<ApiProduct>) =>
    request<ApiProduct>(`/products/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deactivateProduct: (id: number) =>
    request<ApiProduct>(`/products/${id}`, { method: "DELETE" }),
  stores: () => requestAll<ApiStore>("/stores"),
  inventory: () => requestAll<ApiInventory>("/inventory"),
  activities: (storeId?: number) =>
    requestAll<ApiActivity>(
      `/inventory/activities${storeId ? `?store_id=${storeId}` : ""}`,
    ),
  summary: () => request<ApiSummary>("/dashboard/summary"),
  replenishment: (query = "") =>
    requestAll<ApiReplenishment>(`/inventory/replenishment${query}`),
  movement: (
    kind: "sale" | "restock" | "adjustment",
    body: { product_id: number; store_id: number; quantity?: number; quantity_delta?: number; note: string },
    idempotencyKey: string,
  ) =>
    request<{
      id: number;
      quantity_before: number;
      quantity_delta: number;
      quantity_after: number;
    }>(`/inventory/movements/${kind}`, {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify(body),
    }),
  previewImport: (file: File) =>
    request<ImportPreview>(`/inventory/import/preview?filename=${encodeURIComponent(file.name)}`, {
      method: "POST",
      headers: { "Content-Type": "text/csv" },
      body: file,
    }),
  commitImport: (file: File, idempotencyKey: string) =>
    request<ImportResult>(`/inventory/import/commit?filename=${encodeURIComponent(file.name)}`, {
      method: "POST",
      headers: { "Content-Type": "text/csv", "Idempotency-Key": idempotencyKey },
      body: file,
    }),
};
