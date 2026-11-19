import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type ApiActivity, type ApiInventory, type ApiProduct, type ApiReplenishment, type ApiStore, type ApiSummary, type ImportPreview, type ImportResult } from "./api";
import type { Activity, InventoryRow, Product, Store } from "./data";

type MovementType = "Sale" | "Restock" | "Adjustment";
type MovementResult = { previous: number; change: number; result: number };

type AppStore = {
  loading: boolean;
  error: string;
  products: Product[];
  inventory: InventoryRow[];
  activities: Activity[];
  stores: Store[];
  summary: ApiSummary | null;
  replenishment: InventoryRow[];
  refresh: () => Promise<void>;
  addProduct: (product: Omit<Product, "id">) => Promise<Product>;
  updateProduct: (product: Product) => Promise<void>;
  deactivateProduct: (product: Product) => Promise<void>;
  recordMovement: (
    rowId: string,
    type: MovementType,
    amount: number,
    note: string,
    idempotencyKey: string,
  ) => Promise<MovementResult>;
  previewImport: (file: File) => Promise<ImportPreview>;
  commitImport: (file: File, idempotencyKey: string) => Promise<ImportResult>;
};

const StoreContext = createContext<AppStore | null>(null);

const formatTime = (value: string) =>
  new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));

const mapProduct = (value: ApiProduct): Product => ({
  id: value.id,
  sku: value.sku,
  name: value.name,
  category: value.category,
  price: Number(value.price),
});

const mapStore = (value: ApiStore): Store => ({
  id: value.id,
  code: value.code,
  name: value.name,
  location: value.location,
});

const mapInventory = (value: ApiInventory): InventoryRow => ({
  id: String(value.id),
  productId: value.product.id,
  sku: value.product.sku,
  name: value.product.name,
  category: value.product.category,
  price: Number(value.product.price),
  store: value.store.name,
  storeId: value.store.id,
  quantity: value.quantity,
  reorder: value.reorder_level,
  updated: formatTime(value.updated_at),
});

const mapActivity = (value: ApiActivity): Activity => ({
  id: value.id,
  time: formatTime(value.occurred_at),
  type: value.event_type === "csv_import" ? "CSV Import" : (value.event_type[0]?.toUpperCase() + value.event_type.slice(1)) as Activity["type"],
  product: value.product_name,
  sku: value.sku ?? undefined,
  store: value.store_name,
  storeId: value.store_id ?? undefined,
  change: value.quantity_delta,
  note: value.note,
  batch: value.is_batch,
});

const mapReplenishment = (
  value: ApiReplenishment,
  productsById: Map<number, Product>,
  storesById: Map<number, Store>,
): InventoryRow => {
  const product = productsById.get(value.product_id);
  const store = storesById.get(value.store_id);
  return {
    id: String(value.inventory_id),
    productId: value.product_id,
    sku: value.sku,
    name: value.product_name,
    category: product?.category ?? "",
    price: product?.price ?? 0,
    store: value.store_name,
    storeId: value.store_id,
    quantity: value.quantity,
    reorder: value.reorder_level,
    updated: "",
    ...(store?.code ? { storeCode: store.code } : {}),
  };
};

export function StoreProvider({ children }: { children: ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [inventory, setInventory] = useState<InventoryRow[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  const [summary, setSummary] = useState<ApiSummary | null>(null);
  const [replenishment, setReplenishment] = useState<InventoryRow[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [productPage, storePage, inventoryPage, activityPage, summaryData, replenishmentPage] =
        await Promise.all([
          api.products(),
          api.stores(),
          api.inventory(),
          api.activities(),
          api.summary(),
          api.replenishment(),
        ]);
      const nextProducts = productPage.items.map(mapProduct);
      const nextStores = storePage.items.map(mapStore);
      const productsById = new Map(nextProducts.map((product) => [product.id, product]));
      const storesById = new Map(nextStores.map((store) => [store.id, store]));
      setProducts(nextProducts);
      setStores(nextStores);
      setInventory(inventoryPage.items.map(mapInventory));
      setActivities(activityPage.items.map(mapActivity));
      setSummary(summaryData);
      setReplenishment(
        replenishmentPage.items.map((item) =>
          mapReplenishment(item, productsById, storesById),
        ),
      );
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "StockFlow data could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const value = useMemo<AppStore>(
    () => ({
      loading,
      error,
      products,
      inventory,
      activities,
      stores,
      summary,
      replenishment,
      refresh,
      addProduct: async (product) => {
        const created = mapProduct(
          await api.createProduct({ ...product, sku: product.sku.trim().toUpperCase() }),
        );
        await refresh();
        return created;
      },
      updateProduct: async (product) => {
        if (!product.id) throw new Error("Product identifier is missing.");
        await api.updateProduct(product.id, {
          sku: product.sku.trim().toUpperCase(),
          name: product.name.trim(),
          category: product.category,
          price: product.price,
        });
        await refresh();
      },
      deactivateProduct: async (product) => {
        if (!product.id) throw new Error("Product identifier is missing.");
        await api.deactivateProduct(product.id);
        await refresh();
      },
      recordMovement: async (rowId, type, amount, note, idempotencyKey) => {
        const row = inventory.find((item) => item.id === rowId);
        if (!row) throw new Error("Inventory record not found.");
        const kind = type.toLowerCase() as "sale" | "restock" | "adjustment";
        const response = await api.movement(
          kind,
          {
            product_id: row.productId,
            store_id: Number(row.storeId),
            ...(kind === "adjustment" ? { quantity_delta: amount } : { quantity: amount }),
            note,
          },
          idempotencyKey,
        );
        await refresh();
        return {
          previous: response.quantity_before,
          change: response.quantity_delta,
          result: response.quantity_after,
        };
      },
      previewImport: (file) => api.previewImport(file),
      commitImport: async (file, idempotencyKey) => {
        const result = await api.commitImport(file, idempotencyKey);
        await refresh();
        return result;
      },
    }),
    [activities, error, inventory, loading, products, refresh, replenishment, stores, summary],
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useAppStore() {
  const context = useContext(StoreContext);
  if (!context) throw new Error("useAppStore must be used inside StoreProvider");
  return context;
}
