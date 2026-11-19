export type Theme = "ocean" | "forest" | "slate";

export type Product = {
  id: number;
  sku: string;
  name: string;
  category: string;
  price: number;
};

export type Store = {
  id: number;
  code: string;
  name: string;
  location: string;
};

export type InventoryRow = Omit<Product, "id"> & {
  id: string;
  productId: number;
  store: string;
  storeCode?: string;
  storeId: number;
  quantity: number;
  reorder: number;
  updated: string;
};

export type Activity = {
  id: number;
  time: string;
  type: "Sale" | "Restock" | "Adjustment" | "CSV Import";
  product: string;
  sku?: string;
  store: string;
  storeId?: number;
  change: number;
  note: string;
  batch?: boolean;
};
