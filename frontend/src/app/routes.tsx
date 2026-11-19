import {
  Activity,
  AlertTriangle,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpFromLine,
  BadgeCheck,
  Boxes,
  Box,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  ClipboardList,
  FileCheck2,
  FileSpreadsheet,
  Filter,
  History,
  LayoutDashboard,
  MapPin,
  Menu,
  Minus,
  PackagePlus,
  Plus,
  RefreshCcw,
  RotateCcw,
  Search,
  Settings2,
  ShieldAlert,
  ShoppingCart,
  SlidersHorizontal,
  Sparkles,
  Store,
  Tags,
  Upload,
  Warehouse,
  X,
  XCircle,
  type LucideIcon,
} from "lucide-react";
import {
  createBrowserRouter,
  Link,
  NavLink,
  Navigate,
  Outlet,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router";
import { useEffect, useId, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import ImportStudio from "./ImportStudio";
import type { InventoryRow, Product, Theme } from "./data";
import { useAppStore } from "./store";

const navigation: { label: string; path: string; icon: LucideIcon }[] = [
  { label: "Overview", path: "/overview", icon: LayoutDashboard },
  { label: "Catalogue", path: "/catalogue", icon: Tags },
  { label: "Inventory", path: "/inventory", icon: Boxes },
  { label: "Replenishment", path: "/replenishment", icon: RefreshCcw },
  { label: "Data Import", path: "/import", icon: FileSpreadsheet },
];

const categoryOptions = [
  "All categories",
  "Electronics",
  "Accessories",
  "Stationery",
  "Office Supplies",
];

function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 36 36" aria-hidden="true">
      <path
        d="M5 9.2 18 3l13 6.2v17.5L18 33 5 26.7Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <path
        d="m5.8 9.5 12.2 6 12.2-6M18 15.5V33"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <path
        d="m11.4 12.2 12.4-6M12.1 23.2l3 1.5 6.8-3.3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function AppShell() {
  const { error, loading, inventory, stores: activeStores, refresh } = useAppStore();
  const [theme, setTheme] = useState<Theme>("ocean");
  const [navOpen, setNavOpen] = useState(false);
  const [themeOpen, setThemeOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const location = useLocation();
  const active =
    navigation.find((item) => location.pathname.startsWith(item.path)) ?? navigation[0];

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell" data-theme={theme}>
      <aside className={navOpen ? "sidebar open" : "sidebar"}>
        <Link className="brand" to="/overview">
          <BrandMark />
          <span>
            <strong>StockFlow</strong>
            <small>Inventory, in motion</small>
          </span>
        </Link>
        <p className="nav-label">Workspace</p>
        <nav className="primary-nav" aria-label="Primary navigation">
          {navigation.map(({ label, path, icon: Icon }) => (
            <NavLink key={path} to={path} aria-label={label} data-label={label} title={label}>
              <Icon size={19} strokeWidth={1.8} />
              <span>{label}</span>
              <ArrowRight className="nav-arrow" size={15} />
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="demo-note">
            <span className="live-dot" />
            <div>
              <strong>Demonstration workspace</strong>
              <small>Live database · {activeStores.length} active stores</small>
            </div>
          </div>
          <button
            className="sidebar-help"
            aria-label="Open StockFlow guide"
            onClick={() => setHelpOpen(true)}
          >
            <CircleHelp size={18} />
            <span>Prototype guide</span>
          </button>
          <div className="workspace-profile">
            <span>SF</span>
            <div>
              <strong>Academic project</strong>
              <small>Backend connected</small>
            </div>
          </div>
        </div>
      </aside>

      {navOpen && (
        <button
          className="nav-scrim"
          aria-label="Close navigation"
          onClick={() => setNavOpen(false)}
        />
      )}

      <div className="workspace">
        <header className="topbar">
          <div className="topbar-title">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setNavOpen(true)}
            >
              <Menu size={20} />
            </button>
            <span>StockFlow</span>
            <strong>{active.label}</strong>
          </div>
          <div className="topbar-actions">
            <button
              className="icon-button"
            aria-label="Open StockFlow guide"
              onClick={() => setHelpOpen(true)}
            >
              <CircleHelp size={19} />
            </button>
            <div className="theme-control">
              <button
                className="theme-trigger"
                aria-label={`Choose visual theme. Current theme: ${theme}`}
                aria-haspopup="menu"
                aria-expanded={themeOpen}
                onClick={() => setThemeOpen((open) => !open)}
              >
                <span className={`theme-swatch ${theme}`} />
                <span>{theme[0].toUpperCase() + theme.slice(1)}</span>
                <ChevronDown size={15} />
              </button>
              {themeOpen && (
                <div className="theme-menu" role="menu" aria-label="Visual theme">
                  {(["ocean", "forest", "slate"] as Theme[]).map((item) => (
                    <button
                      key={item}
                      className={item === theme ? "selected" : ""}
                      role="menuitemradio"
                      aria-checked={item === theme}
                      onClick={() => {
                        setTheme(item);
                        setThemeOpen(false);
                      }}
                    >
                      <span className={`theme-swatch ${item}`} />
                      <span>{item[0].toUpperCase() + item.slice(1)}</span>
                      {item === theme && <Check size={15} />}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div className="avatar">SF</div>
          </div>
        </header>
        <main className="page" id="main-content">
          {error && (
            <div className="api-error-banner" role="alert">
              <AlertTriangle size={18} />
              <span>{error}</span>
              <Button variant="secondary" onClick={() => void refresh()}>
                Retry
              </Button>
            </div>
          )}
          {loading && inventory.length === 0 ? (
            <div className="empty-state" role="status">Loading StockFlow data…</div>
          ) : error && inventory.length === 0 ? null : (
            <Outlet />
          )}
        </main>
      </div>

      {helpOpen && (
        <Dialog title="StockFlow guide" eyebrow="STOCKFLOW" onClose={() => setHelpOpen(false)}>
          <div className="guide-content">
            <p>
              StockFlow reads persistent product, inventory, movement and activity data from the
              connected backend.
            </p>
            <ul>
              <li>Choose an alert to carry its product and store into Inventory.</li>
              <li>Record a movement to update balances and persistent movement history.</li>
              <li>Preview a CSV, correct rejected rows, then commit the entire valid batch.</li>
            </ul>
            <p className="notice">
              <CircleHelp size={17} /> Inventory changes persist in PostgreSQL and remain after
              refresh.
            </p>
          </div>
          <div className="dialog-footer">
            <Button onClick={() => setHelpOpen(false)}>Understood</Button>
          </div>
        </Dialog>
      )}
    </div>
  );
}

function PageHeader({
  title,
  description,
  action,
  meta,
}: {
  title: string;
  description: string;
  action?: ReactNode;
  meta?: string;
}) {
  return (
    <div className="page-header">
      <div>
        <div className="breadcrumb">
          <span>StockFlow</span>
          <ArrowRight size={12} />
          <span>{title}</span>
        </div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="page-header-side">
        {meta && <span className="data-as-of">{meta}</span>}
        {action}
      </div>
    </div>
  );
}

function Button({
  children,
  variant = "primary",
  icon: Icon,
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  icon?: LucideIcon;
}) {
  return (
    <button {...props} className={`button ${variant} ${className}`}>
      {Icon && <Icon size={17} />}
      {children}
    </button>
  );
}

function Dialog({
  title,
  eyebrow,
  onClose,
  children,
  wide,
}: {
  title: string;
  eyebrow: string;
  onClose: () => void;
  children: ReactNode;
  wide?: boolean;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLElement | null>(null);
  const closeRef = useRef(onClose);
  useEffect(() => {
    closeRef.current = onClose;
  }, [onClose]);
  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current;
    const focusable = () =>
      Array.from(
        dialog?.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href]',
        ) ?? [],
      ).filter((element) => element.offsetParent !== null);
    requestAnimationFrame(() => focusable()[0]?.focus());
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeRef.current();
      }
      if (event.key === "Tab") {
        const items = focusable();
        if (!items.length) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      window.removeEventListener("keydown", closeOnEscape);
      previousFocus?.focus();
    };
  }, []);

  return (
    <div
      className="dialog-backdrop"
      onMouseDown={(event) => event.target === event.currentTarget && onClose()}
    >
      <section
        ref={dialogRef}
        className={wide ? "dialog wide" : "dialog"}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="dialog-head">
          <div>
            <span className="eyebrow">{eyebrow}</span>
            <h2 id={titleId}>{title}</h2>
          </div>
          <button className="icon-button" aria-label="Close dialog" onClick={onClose}>
            <X size={19} />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

function StockStatus({
  quantity,
  reorder,
  compact = false,
}: {
  quantity: number;
  reorder: number;
  compact?: boolean;
}) {
  const status =
    quantity === 0 ? "Out of stock" : quantity <= reorder ? "Below reorder" : "Healthy";
  const tone = quantity === 0 ? "critical" : quantity <= reorder ? "warning" : "healthy";
  return (
    <span className={`stock-status ${tone} ${compact ? "compact" : ""}`}>
      <i />
      {status}
    </span>
  );
}

function Threshold({ quantity, reorder }: { quantity: number; reorder: number }) {
  const percent = Math.min(100, Math.round((quantity / Math.max(reorder * 2, 1)) * 100));
  return (
    <div className="threshold">
      <div className="threshold-values">
        <strong>{quantity}</strong>
        <span>/ {reorder} reorder</span>
      </div>
      <div className="threshold-track">
        <span
          className={quantity === 0 ? "critical" : quantity <= reorder ? "warning" : "healthy"}
          style={{ width: `${percent}%` }}
        />
        <i style={{ left: "50%" }} />
      </div>
    </div>
  );
}

function EventIcon({ type }: { type: string }) {
  const Icon =
    type === "Sale"
      ? ShoppingCart
      : type === "Restock"
        ? ArrowDownToLine
        : type === "Adjustment"
          ? SlidersHorizontal
          : FileSpreadsheet;
  return (
    <span className={`event-icon ${type.toLowerCase().replace(" ", "-")}`}>
      <Icon size={16} />
    </span>
  );
}

function Overview() {
  const { inventory, products, activities, stores, summary, replenishment } = useAppStore();
  const navigate = useNavigate();
  const total = summary?.total_units ?? 0;
  const lowCount = summary?.low_balances ?? 0;
  const outCount = summary?.out_of_stock_balances ?? 0;
  const healthy = summary?.healthy_balances ?? 0;
  const attention = replenishment.slice(0, 5);

  const openContext = (row: InventoryRow, destination: "inventory" | "replenishment") => {
    navigate(`/${destination}?store=${encodeURIComponent(row.store)}&sku=${row.sku}`);
  };

  return (
    <>
      <PageHeader
        title="Overview"
        description="A concise view of stock health across your retail network."
        meta="Live database data"
      />
      <section className="overview-hero">
        <div className="total-stock">
          <span className="metric-kicker">
            <Boxes size={17} /> Total stock units
          </span>
          <strong>{total.toLocaleString("en-IN")}</strong>
          <p>Available across all active locations</p>
          <div className="compact-facts">
            <span>
              <b>{products.length}</b> products
            </span>
            <span>
              <b>{stores.length}</b> stores
            </span>
            <span>
              <b>{summary?.category_count ?? 0}</b> categories
            </span>
          </div>
        </div>
        <div className="attention-summary">
          <span className="metric-kicker">
            <ShieldAlert size={17} /> Attention required
          </span>
          <div className="attention-numbers">
            <button onClick={() => navigate("/replenishment?urgency=out")}>
              <strong>{outCount}</strong>
              <span>Out of stock</span>
              <ArrowRight size={17} />
            </button>
            <button onClick={() => navigate("/replenishment?urgency=low")}>
              <strong>{lowCount}</strong>
              <span>Below reorder</span>
              <ArrowRight size={17} />
            </button>
          </div>
          <p>Resolve out-of-stock records first, then restore low stock to target.</p>
        </div>
      </section>

      <section className="stock-health section-block">
        <div className="section-heading">
          <div>
            <span className="section-index">01</span>
            <h2>Stock health</h2>
          </div>
          <p>Store-level records, not misleading product aggregates.</p>
        </div>
        <div
          className="health-bar"
          aria-label={`${healthy} healthy, ${lowCount} below reorder, ${outCount} out of stock`}
        >
          <span className="healthy" style={{ flex: healthy }} />
          <span className="warning" style={{ flex: lowCount }} />
          <span className="critical" style={{ flex: outCount }} />
        </div>
        <div className="health-legend">
          <div>
            <i className="healthy" />
            <span>Healthy</span>
            <strong>{healthy}</strong>
          </div>
          <div>
            <i className="warning" />
            <span>Below reorder</span>
            <strong>{lowCount}</strong>
          </div>
          <div>
            <i className="critical" />
            <span>Out of stock</span>
            <strong>{outCount}</strong>
          </div>
          <small>{summary?.total_balances ?? inventory.length} store-level balances</small>
        </div>
      </section>

      <div className="overview-grid">
        <section className="section-block alert-list">
          <div className="section-heading">
            <div>
              <span className="section-index">02</span>
              <h2>Inventory alerts</h2>
            </div>
            <Link to="/replenishment">
              Open queue <ArrowRight size={15} />
            </Link>
          </div>
          {attention.map((item, index) => (
            <article className="alert-item" key={item.id}>
              <span
                className={
                  item.quantity === 0 ? "priority-number critical" : "priority-number warning"
                }
              >
                {String(index + 1).padStart(2, "0")}
              </span>
              <div className="alert-product">
                <strong>{item.name}</strong>
                <span>
                  <MapPin size={13} />
                  {item.store} · {item.sku}
                </span>
              </div>
              <Threshold quantity={item.quantity} reorder={item.reorder} />
              <Button variant="ghost" onClick={() => openContext(item, "inventory")}>
                Inspect <ArrowRight size={15} />
              </Button>
              <Button variant="secondary" onClick={() => openContext(item, "replenishment")}>
                Restock
              </Button>
            </article>
          ))}
        </section>
        <section className="section-block recent-activity">
          <div className="section-heading">
            <div>
              <span className="section-index">03</span>
              <h2>Recent activity</h2>
            </div>
            <Link to="/inventory?tab=history">
              View history <ArrowRight size={15} />
            </Link>
          </div>
          {activities.slice(0, 5).map((event) => (
            <article className="activity-item" key={event.id}>
              <EventIcon type={event.type} />
              <div>
                <strong>{event.type}</strong>
                <span>
                  {event.product} · {event.store}
                </span>
                <small>{event.time}</small>
              </div>
              <b className={event.change >= 0 ? "positive" : "negative"}>
                {event.change > 0 ? "+" : ""}
                {event.change}
              </b>
            </article>
          ))}
        </section>
      </div>
    </>
  );
}

function Catalogue() {
  const { products, inventory, addProduct, updateProduct, deactivateProduct } = useAppStore();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All categories");
  const [sort, setSort] = useState("name");
  const [dialog, setDialog] = useState(false);
  const [success, setSuccess] = useState("");
  const [editing, setEditing] = useState<Product | null>(null);
  const [operationError, setOperationError] = useState("");
  const filtered = useMemo(() => {
    const list = products.filter(
      (product) =>
        (category === "All categories" || product.category === category) &&
        `${product.name} ${product.sku}`.toLowerCase().includes(search.toLowerCase()),
    );
    return [...list].sort((a, b) =>
      sort === "stock"
        ? inventory.filter((row) => row.sku === b.sku).reduce((sum, row) => sum + row.quantity, 0) -
          inventory.filter((row) => row.sku === a.sku).reduce((sum, row) => sum + row.quantity, 0)
        : a.name.localeCompare(b.name),
    );
  }, [category, inventory, products, search, sort]);
  const clear = () => {
    setSearch("");
    setCategory("All categories");
    setSort("name");
  };

  return (
    <>
      <PageHeader
        title="Catalogue"
        description="Maintain product definitions independently from store-level stock."
        action={
          <Button icon={Plus} onClick={() => setDialog(true)}>
            Add product
          </Button>
        }
      />
      {success && (
        <div className="success-banner">
          <CheckCircle2 size={19} />
          <span>
            <strong>Catalogue updated.</strong> {success}
          </span>
          <button aria-label="Dismiss product confirmation" onClick={() => setSuccess("")}>
            <X size={17} />
          </button>
        </div>
      )}
      <div className="toolbar">
        <label className="search-field">
          <Search size={17} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or SKU"
          />
        </label>
        <div className="toolbar-filters">
          <label>
            <Filter size={16} />
            <select
              aria-label="Category filter"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              {categoryOptions.map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>
          <label>
            <Settings2 size={16} />
            <select
              aria-label="Sort products"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="name">Sort: Product name</option>
              <option value="stock">Sort: Total stock</option>
            </select>
          </label>
          <Button
            variant="ghost"
            icon={RotateCcw}
            onClick={clear}
            disabled={!search && category === "All categories" && sort === "name"}
          >
            Clear
          </Button>
        </div>
      </div>
      <section className="data-surface">
        <div className="table-caption">
          <span>{filtered.length} product definitions</span>
          <small>Stock health is shown by store coverage, not an aggregate badge.</small>
        </div>
        <div className="desktop-table">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>SKU</th>
                <th>Category</th>
                <th>Unit price</th>
                <th>Total stock</th>
                <th>Store coverage</th>
                <th>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((product) => (
                <CatalogueRow
                  key={product.sku}
                  product={product}
                  onEdit={() => setEditing(product)}
                  onDeactivate={() => {
                    if (!window.confirm(`Deactivate ${product.name}? Historical activity will remain.`)) return;
                    void deactivateProduct(product).then(
                      () => setSuccess(`${product.name} was deactivated.`),
                      (error: unknown) => setOperationError(error instanceof Error ? error.message : "Product could not be deactivated."),
                    );
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>
        <div className="mobile-records">
          {filtered.map((product) => (
            <CatalogueCard
              key={product.sku}
              product={product}
              onEdit={() => setEditing(product)}
              onDeactivate={() => {
                if (!window.confirm(`Deactivate ${product.name}? Historical activity will remain.`)) return;
                void deactivateProduct(product).then(
                  () => setSuccess(`${product.name} was deactivated.`),
                  (error: unknown) => setOperationError(error instanceof Error ? error.message : "Product could not be deactivated."),
                );
              }}
            />
          ))}
        </div>
        {!filtered.length && (
          <EmptyState
            icon={Search}
            title="No matching products"
            text="Try a different name, SKU or category."
            action={
              <Button variant="secondary" onClick={clear}>
                Clear filters
              </Button>
            }
          />
        )}
      </section>
      {operationError && <div className="api-error-banner" role="alert">{operationError}</div>}
      {dialog && (
        <ProductDialog
          onClose={() => setDialog(false)}
          onSave={async (product) => {
            const created = await addProduct(product);
            setSuccess(created.name);
            setDialog(false);
          }}
          existing={products}
        />
      )}
      {editing && (
        <ProductDialog
          initial={editing}
          onClose={() => setEditing(null)}
          onSave={async (product) => {
            await updateProduct({ ...product, id: editing.id });
            setSuccess(`${product.name} was updated.`);
            setEditing(null);
          }}
          existing={products.filter((product) => product.id !== editing.id)}
        />
      )}
    </>
  );
}

function useCoverage(product: Product) {
  const { inventory } = useAppStore();
  const rows = inventory.filter((row) => row.sku === product.sku);
  return {
    total: rows.reduce((sum, row) => sum + row.quantity, 0),
    healthy: rows.filter((row) => row.quantity > row.reorder).length,
    low: rows.filter((row) => row.quantity > 0 && row.quantity <= row.reorder).length,
    out: rows.filter((row) => row.quantity === 0).length,
  };
}

function CatalogueRow({
  product,
  onEdit,
  onDeactivate,
}: {
  product: Product;
  onEdit: () => void;
  onDeactivate: () => void;
}) {
  const coverage = useCoverage(product);
  return (
    <tr>
      <td>
        <span className="product-cell">
          <span className="product-glyph">
            <Box size={18} />
          </span>
          <strong>{product.name}</strong>
        </span>
      </td>
      <td className="mono">{product.sku}</td>
      <td>{product.category}</td>
      <td className="numeric">₹{product.price.toLocaleString("en-IN")}</td>
      <td className="numeric">
        <strong>{coverage.total}</strong> units
      </td>
      <td>
        <span className="coverage">
          <b>{coverage.healthy} healthy</b>
          {coverage.low > 0 && <span> · {coverage.low} low</span>}
          {coverage.out > 0 && <em> · {coverage.out} out</em>}
          {coverage.total === 0 && <span>Not stocked</span>}
        </span>
      </td>
      <td>
        <div className="row-actions">
          <Link className="row-link" to={`/inventory?sku=${product.sku}`}>View stock</Link>
          <button aria-label={`Edit ${product.name}`} onClick={onEdit}><Settings2 size={16} /></button>
          <button aria-label={`Deactivate ${product.name}`} onClick={onDeactivate}><XCircle size={16} /></button>
        </div>
      </td>
    </tr>
  );
}

function CatalogueCard({
  product,
  onEdit,
  onDeactivate,
}: {
  product: Product;
  onEdit: () => void;
  onDeactivate: () => void;
}) {
  const coverage = useCoverage(product);
  return (
    <article className="mobile-card">
      <div className="mobile-card-head">
        <span className="product-glyph">
          <Box size={18} />
        </span>
        <div>
          <strong>{product.name}</strong>
          <span>
            {product.sku} · {product.category}
          </span>
        </div>
        <b>₹{product.price.toLocaleString("en-IN")}</b>
      </div>
      <div className="mobile-card-stats">
        <span>
          Total stock <strong>{coverage.total}</strong>
        </span>
        <span>
          Coverage{" "}
          <strong>
            {coverage.healthy} healthy · {coverage.out} out
          </strong>
        </span>
      </div>
      <Link className="button secondary" to={`/inventory?sku=${product.sku}`}>
        View inventory
      </Link>
      <div className="mobile-actions">
        <Button variant="secondary" onClick={onEdit}>Edit</Button>
        <Button variant="danger" onClick={onDeactivate}>Deactivate</Button>
      </div>
    </article>
  );
}

function ProductDialog({
  onClose,
  onSave,
  existing,
  initial,
}: {
  onClose: () => void;
  onSave: (product: Omit<Product, "id"> & { id?: number }) => Promise<void>;
  existing: Product[];
  initial?: Product;
}) {
  const [form, setForm] = useState({
    name: initial?.name ?? "",
    sku: initial?.sku ?? "",
    category: initial?.category ?? "Electronics",
    price: initial ? String(initial.price) : "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const next: Record<string, string> = {};
    if (!form.name.trim()) next.name = "Enter a product name.";
    if (!form.sku.trim()) next.sku = "Enter a SKU.";
    else if (
      existing.some((product) => product.sku.toLowerCase() === form.sku.trim().toLowerCase())
    )
      next.sku = "This SKU already exists.";
    if (!form.price || Number(form.price) < 0) next.price = "Enter a valid non-negative price.";
    setErrors(next);
    if (Object.keys(next).length) return;
    setSaving(true);
    try {
      await onSave({
        ...(initial?.id ? { id: initial.id } : {}),
        name: form.name.trim(),
        sku: form.sku.trim().toUpperCase(),
        category: form.category,
        price: Number(form.price),
      });
    } catch (caught) {
      setErrors({ submit: caught instanceof Error ? caught.message : "Product could not be saved." });
    } finally {
      setSaving(false);
    }
  };
  return (
    <Dialog title={initial ? "Edit product" : "Add product"} eyebrow="CATALOGUE" onClose={onClose}>
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Product name" error={errors.name}>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Portable SSD"
            />
          </Field>
          <Field label="SKU" error={errors.sku}>
            <input
              className="mono"
              value={form.sku}
              onChange={(e) => setForm({ ...form, sku: e.target.value })}
              placeholder="e.g. EL-006"
            />
          </Field>
          <Field label="Category">
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
            >
              {categoryOptions.slice(1).map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </Field>
          <Field label="Unit price (₹)" error={errors.price}>
            <input
              type="number"
              min="0"
              value={form.price}
              onChange={(e) => setForm({ ...form, price: e.target.value })}
              placeholder="0.00"
            />
          </Field>
        </div>
        {errors.submit && <p className="field-error" role="alert">{errors.submit}</p>}
        <div className="dialog-footer">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>{saving ? "Saving…" : initial ? "Save changes" : "Save product"}</Button>
        </div>
      </form>
    </Dialog>
  );
}

function Field({
  label,
  error,
  children,
  hint,
}: {
  label: string;
  error?: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className={error ? "field error" : "field"}>
      <span>{label}</span>
      {children}
      {error && (
        <small>
          <AlertTriangle size={13} />
          {error}
        </small>
      )}
      {hint && !error && <small>{hint}</small>}
    </label>
  );
}

type MovementMode = "Sale" | "Restock" | "Adjustment";

function Inventory() {
  const { inventory, activities, stores: activeStores } = useAppStore();
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "history" ? "history" : "balances";
  const contextStore = params.get("store") ?? "All Stores";
  const contextSku = params.get("sku") ?? "";
  const [store, setStore] = useState(contextStore);
  const [search, setSearch] = useState(contextSku);
  const [status, setStatus] = useState("All statuses");
  const [movement, setMovement] = useState<{ row: InventoryRow; mode: MovementMode } | null>(null);
  const [feedback, setFeedback] = useState("");
  const rows = inventory.filter(
    (row) =>
      (store === "All Stores" || row.store === store) &&
      `${row.name} ${row.sku}`.toLowerCase().includes(search.toLowerCase()) &&
      (status === "All statuses" ||
        (status === "Healthy" && row.quantity > row.reorder) ||
        (status === "Below reorder" && row.quantity > 0 && row.quantity <= row.reorder) ||
        (status === "Out of stock" && row.quantity === 0)),
  );
  const setTab = (next: "balances" | "history") => {
    const nextParams = new URLSearchParams(params);
    if (next === "history") nextParams.set("tab", "history");
    else nextParams.delete("tab");
    setParams(nextParams);
  };
  const selectedStoreCount = rows.reduce((sum, row) => sum + row.quantity, 0);

  return (
    <>
      <PageHeader
        title="Inventory"
        description="Inspect store-level balances and record every stock movement in context."
        action={
          <Button
            icon={PackagePlus}
            onClick={() => rows[0] && setMovement({ row: rows[0], mode: "Sale" })}
            disabled={!rows.length}
          >
            Record stock movement
          </Button>
        }
      />
      {feedback && (
        <div className="success-banner">
          <CheckCircle2 size={19} />
          <span>{feedback}</span>
          <button aria-label="Dismiss inventory confirmation" onClick={() => setFeedback("")}>
            <X size={17} />
          </button>
        </div>
      )}
      <div className="inventory-context">
        <label className="store-select">
          <Store size={18} />
          <span>
            <small>Store context</small>
            <select value={store} onChange={(e) => setStore(e.target.value)}>
              <option>All Stores</option>
              {activeStores.map((item) => (
                <option key={item.id}>{item.name}</option>
              ))}
            </select>
          </span>
        </label>
        <div>
          <span>Visible units</span>
          <strong>{selectedStoreCount}</strong>
        </div>
        <div>
          <span>Below reorder</span>
          <strong className="warning-text">
            {rows.filter((row) => row.quantity > 0 && row.quantity <= row.reorder).length}
          </strong>
        </div>
        <div>
          <span>Out of stock</span>
          <strong className="negative">{rows.filter((row) => row.quantity === 0).length}</strong>
        </div>
      </div>
      <div className="tabs" role="tablist" aria-label="Inventory views">
        <button
          role="tab"
          aria-selected={tab === "balances"}
          className={tab === "balances" ? "active" : ""}
          onClick={() => setTab("balances")}
        >
          <Boxes size={17} />
          Stock Balances
        </button>
        <button
          role="tab"
          aria-selected={tab === "history"}
          className={tab === "history" ? "active" : ""}
          onClick={() => setTab("history")}
        >
          <History size={17} />
          Movement History
        </button>
      </div>
      {tab === "balances" ? (
        <>
          <div className="toolbar">
            <label className="search-field">
              <Search size={17} />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search product or SKU"
              />
            </label>
            <div className="toolbar-filters">
              <label>
                <Filter size={16} />
                <select
                  aria-label="Stock status filter"
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                >
                  <option>All statuses</option>
                  <option>Healthy</option>
                  <option>Below reorder</option>
                  <option>Out of stock</option>
                </select>
              </label>
              <Button
                variant="ghost"
                icon={RotateCcw}
                onClick={() => {
                  setSearch("");
                  setStatus("All statuses");
                }}
                disabled={!search && status === "All statuses"}
              >
                Clear
              </Button>
            </div>
          </div>
          <section className="data-surface inventory-table">
            <div className="table-caption">
              <span>{rows.length} store-level balances</span>
              <small>The marker shows the reorder threshold.</small>
            </div>
            <div className="desktop-table">
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>SKU</th>
                    <th>Store</th>
                    <th>Available / reorder</th>
                    <th>Status</th>
                    <th>Last updated</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <InventoryRowView
                      key={row.id}
                      row={row}
                      onMove={(mode) => setMovement({ row, mode })}
                    />
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mobile-records">
              {rows.map((row) => (
                <InventoryCard
                  key={row.id}
                  row={row}
                  onMove={(mode) => setMovement({ row, mode })}
                />
              ))}
            </div>
            {!rows.length && (
              <EmptyState
                icon={Search}
                title="No balances match"
                text="Change the store, product search or status filter."
                action={
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setSearch("");
                      setStatus("All statuses");
                      setStore("All Stores");
                    }}
                  >
                    Reset view
                  </Button>
                }
              />
            )}
          </section>
        </>
      ) : (
        <MovementHistory activities={activities} store={store} />
      )}
      {movement && (
        <MovementDialog
          initialRow={movement.row}
          initialMode={movement.mode}
          onClose={() => setMovement(null)}
          onComplete={(message) => {
            setFeedback(message);
            setMovement(null);
          }}
        />
      )}
    </>
  );
}

function InventoryRowView({
  row,
  onMove,
}: {
  row: InventoryRow;
  onMove: (mode: MovementMode) => void;
}) {
  return (
    <tr className={row.quantity === 0 ? "critical-row" : ""}>
      <td>
        <span className="product-cell">
          <span className="product-glyph">
            <Box size={18} />
          </span>
          <strong>{row.name}</strong>
        </span>
      </td>
      <td className="mono">{row.sku}</td>
      <td>
        <span className="location-cell">
          <MapPin size={15} />
          {row.store}
        </span>
      </td>
      <td>
        <Threshold quantity={row.quantity} reorder={row.reorder} />
      </td>
      <td>
        <StockStatus quantity={row.quantity} reorder={row.reorder} />
      </td>
      <td>
        <span className="muted">{row.updated}</span>
      </td>
      <td>
        <div className="row-actions">
          <button
            aria-label={`Record sale for ${row.name}`}
            title="Sale"
            onClick={() => onMove("Sale")}
          >
            <ShoppingCart size={16} />
          </button>
          <button
            aria-label={`Restock ${row.name}`}
            title="Restock"
            onClick={() => onMove("Restock")}
          >
            <ArrowDownToLine size={16} />
          </button>
          <button
            aria-label={`Adjust ${row.name}`}
            title="Adjustment"
            onClick={() => onMove("Adjustment")}
          >
            <SlidersHorizontal size={16} />
          </button>
        </div>
      </td>
    </tr>
  );
}

function InventoryCard({
  row,
  onMove,
}: {
  row: InventoryRow;
  onMove: (mode: MovementMode) => void;
}) {
  return (
    <article className="mobile-card inventory-card">
      <div className="mobile-card-head">
        <span className="product-glyph">
          <Box size={18} />
        </span>
        <div>
          <strong>{row.name}</strong>
          <span>
            {row.sku} · {row.store}
          </span>
        </div>
        <StockStatus compact quantity={row.quantity} reorder={row.reorder} />
      </div>
      <Threshold quantity={row.quantity} reorder={row.reorder} />
      <div className="mobile-actions">
        <Button variant="secondary" icon={ShoppingCart} onClick={() => onMove("Sale")}>
          Sale
        </Button>
        <Button variant="secondary" icon={ArrowDownToLine} onClick={() => onMove("Restock")}>
          Restock
        </Button>
        <button
          className="icon-button"
          aria-label={`Adjust stock for ${row.name} at ${row.store}`}
          onClick={() => onMove("Adjustment")}
        >
          <SlidersHorizontal size={17} />
        </button>
      </div>
    </article>
  );
}

function MovementHistory({
  activities,
  store,
}: {
  activities: ReturnType<typeof useAppStore>["activities"];
  store: string;
}) {
  const [search, setSearch] = useState("");
  const [type, setType] = useState("All events");
  const rows = activities.filter(
    (activity) =>
      (store === "All Stores" || activity.store === store) &&
      (type === "All events" || activity.type === type) &&
      `${activity.product} ${activity.store} ${activity.note}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <div className="toolbar">
        <label className="search-field">
          <Search size={17} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search movement history"
          />
        </label>
        <div className="toolbar-filters">
          <label>
            <Filter size={16} />
            <select
              aria-label="Movement type filter"
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              <option>All events</option>
              <option>Sale</option>
              <option>Restock</option>
              <option>Adjustment</option>
              <option>CSV Import</option>
            </select>
          </label>
        </div>
      </div>
      <section className="data-surface">
        <div className="table-caption">
          <span>{rows.length} recorded events</span>
          <small>CSV imports appear as batch events.</small>
        </div>
        <div className="desktop-table">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Event type</th>
                <th>Product / batch</th>
                <th>Store</th>
                <th>Quantity change</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((activity) => (
                <tr key={activity.id}>
                  <td className="muted">{activity.time}</td>
                  <td>
                    <span className="event-label">
                      <EventIcon type={activity.type} />
                      {activity.type}
                    </span>
                  </td>
                  <td>
                    <strong>{activity.product}</strong>
                    {activity.sku && <small className="table-sub">{activity.sku}</small>}
                  </td>
                  <td>{activity.store}</td>
                  <td className={`numeric ${activity.change >= 0 ? "positive" : "negative"}`}>
                    <strong>
                      {activity.change > 0 ? "+" : ""}
                      {activity.change}
                    </strong>{" "}
                    units
                  </td>
                  <td className="muted">{activity.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mobile-records">
          {rows.map((activity) => (
            <article className="mobile-card history-card" key={activity.id}>
              <EventIcon type={activity.type} />
              <div>
                <strong>
                  {activity.type} · {activity.product}
                </strong>
                <span>
                  {activity.store} · {activity.time}
                </span>
                <small>{activity.note}</small>
              </div>
              <b className={activity.change >= 0 ? "positive" : "negative"}>
                {activity.change > 0 ? "+" : ""}
                {activity.change}
              </b>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

function MovementDialog({
  initialRow,
  initialMode,
  onClose,
  onComplete,
}: {
  initialRow: InventoryRow;
  initialMode: MovementMode;
  onClose: () => void;
  onComplete: (message: string) => void;
}) {
  const { inventory, recordMovement } = useAppStore();
  const [rowId, setRowId] = useState(initialRow.id);
  const [mode, setMode] = useState(initialMode);
  const [amount, setAmount] = useState(
    initialMode === "Restock"
      ? String(Math.max(initialRow.reorder * 2 - initialRow.quantity, 1))
      : "",
  );
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const idempotencyKey = useRef(crypto.randomUUID());
  const resetIdempotencyKey = () => {
    idempotencyKey.current = crypto.randomUUID();
  };
  const [result, setResult] = useState<{ previous: number; change: number; result: number } | null>(
    null,
  );
  const row = inventory.find((item) => item.id === rowId) ?? initialRow;
  const numericAmount = Number(amount || 0);
  const change =
    mode === "Sale"
      ? -Math.abs(numericAmount)
      : mode === "Restock"
        ? Math.abs(numericAmount)
        : numericAmount;
  const projected = row.quantity + change;
  useEffect(() => {
    if (mode === "Restock" && !amount)
      setAmount(String(Math.max(row.reorder * 2 - row.quantity, 1)));
  }, [amount, mode, row.quantity, row.reorder]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!amount || numericAmount === 0) return setError("Enter a quantity greater than zero.");
    if (mode !== "Adjustment" && numericAmount < 0) return setError("Enter a positive quantity.");
    if (projected < 0)
      return setError(`Only ${row.quantity} units are available. Reduce the sale quantity.`);
    setPending(true);
    try {
      setResult(await recordMovement(row.id, mode, numericAmount, note, idempotencyKey.current));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Movement could not be recorded.");
    } finally {
      setPending(false);
    }
  };
  if (result)
    return (
      <Dialog title="Movement recorded" eyebrow="INVENTORY UPDATED" onClose={onClose}>
        <div className="success-result">
          <span className="success-icon">
            <Check size={25} />
          </span>
          <h3>
            {row.name} · {row.store}
          </h3>
          <p>The {mode.toLowerCase()} has updated this store-level balance.</p>
          <div className="result-equation">
            <div>
              <span>Previous</span>
              <strong>{result.previous}</strong>
            </div>
            <i>{result.change >= 0 ? "+" : "−"}</i>
            <div>
              <span>
                {mode === "Sale"
                  ? "Quantity sold"
                  : mode === "Restock"
                    ? "Quantity added"
                    : "Adjustment"}
              </span>
              <strong>{Math.abs(result.change)}</strong>
            </div>
            <i>=</i>
            <div className="result-total">
              <span>Resulting stock</span>
              <strong>{result.result}</strong>
            </div>
          </div>
        </div>
        <div className="dialog-footer">
          <Button
            onClick={() =>
              onComplete(
                `${mode} recorded for ${row.name} at ${row.store}. Resulting stock: ${result.result} units.`,
              )
            }
          >
            Done
          </Button>
        </div>
      </Dialog>
    );
  return (
    <Dialog
      title="Record stock movement"
      eyebrow={`${row.store.toUpperCase()} · ${row.sku}`}
      onClose={onClose}
      wide
    >
      <form onSubmit={submit}>
        <div className="movement-types">
          {(["Sale", "Restock", "Adjustment"] as MovementMode[]).map((item) => {
            const Icon =
              item === "Sale"
                ? ShoppingCart
                : item === "Restock"
                  ? ArrowDownToLine
                  : SlidersHorizontal;
            return (
              <button
                type="button"
                disabled={pending}
                className={mode === item ? "active" : ""}
                key={item}
                onClick={() => {
                  resetIdempotencyKey();
                  setMode(item);
                  setError("");
                  setAmount(
                    item === "Restock" ? String(Math.max(row.reorder * 2 - row.quantity, 1)) : "",
                  );
                }}
              >
                <Icon size={18} />
                <span>
                  <strong>{item}</strong>
                  <small>
                    {item === "Sale"
                      ? "Decrease stock"
                      : item === "Restock"
                        ? "Increase stock"
                        : "Correct stock"}
                  </small>
                </span>
              </button>
            );
          })}
        </div>
        <div className="movement-context">
          <div>
            <span>Product</span>
            <strong>{row.name}</strong>
            <small>{row.sku}</small>
          </div>
          <div>
            <span>Store</span>
            <strong>{row.store}</strong>
            <small>{row.storeId}</small>
          </div>
          <div>
            <span>Current stock</span>
            <strong>{row.quantity} units</strong>
            <small>Reorder at {row.reorder}</small>
          </div>
        </div>
        <div className="form-grid">
          <Field label="Product">
            <select
              value={rowId}
              disabled={pending}
              onChange={(e) => {
                resetIdempotencyKey();
                setRowId(e.target.value);
                setError("");
              }}
            >
              {inventory.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} · {item.store}
                </option>
              ))}
            </select>
          </Field>
          <Field
            label={
              mode === "Adjustment"
                ? "Adjustment amount"
                : mode === "Sale"
                  ? "Quantity sold"
                  : "Quantity received"
            }
            error={error}
          >
            <input
              autoFocus
              type="number"
              min={mode === "Adjustment" ? undefined : "1"}
              value={amount}
              disabled={pending}
              onChange={(e) => {
                resetIdempotencyKey();
                setAmount(e.target.value);
                setError("");
              }}
              placeholder={mode === "Adjustment" ? "Use + or −" : "Enter units"}
            />
          </Field>
          <Field label={mode === "Adjustment" ? "Reason" : "Notes (optional)"}>
            <textarea
              value={note}
              disabled={pending}
              onChange={(e) => {
                resetIdempotencyKey();
                setNote(e.target.value);
              }}
              placeholder={
                mode === "Adjustment"
                  ? "Explain the stock correction"
                  : "Add a reference or delivery note"
              }
            />
          </Field>
          <div className={projected < 0 ? "quantity-preview invalid" : "quantity-preview"}>
            <span>Resulting quantity</span>
            <div>
              <b>{row.quantity}</b>
              <i>{change >= 0 ? "+" : "−"}</i>
              <b>{Math.abs(change)}</b>
              <i>=</i>
              <strong>{projected}</strong>
              <small>units</small>
            </div>
            {projected < 0 && <p>Stock cannot fall below zero.</p>}
          </div>
        </div>
        <div className="dialog-footer">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!amount || projected < 0 || pending}>
            {pending ? "Saving…" : `Confirm ${mode.toLowerCase()}`}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}

function Replenishment() {
  const { replenishment, stores: activeStores } = useAppStore();
  const [params] = useSearchParams();
  const initialStore = params.get("store") ?? "All Stores";
  const focusSku = params.get("sku");
  const urgency = params.get("urgency");
  const [store, setStore] = useState(initialStore);
  const [restock, setRestock] = useState<InventoryRow | null>(null);
  const [feedback, setFeedback] = useState("");
  const queue = replenishment.filter(
    (row) =>
      (store === "All Stores" || row.store === store) &&
      (urgency === "out" ? row.quantity === 0 : urgency === "low" ? row.quantity > 0 : true),
  );
  const sorted = focusSku
    ? [...queue].sort((a, b) => Number(b.sku === focusSku) - Number(a.sku === focusSku))
    : queue;
  const out = sorted.filter((row) => row.quantity === 0);
  const low = sorted.filter((row) => row.quantity > 0);
  return (
    <>
      <PageHeader
        title="Replenishment"
        description="A focused queue for restoring stock to a simple, visible target."
        action={
          <label className="header-select">
            <MapPin size={17} />
            <select value={store} onChange={(e) => setStore(e.target.value)}>
              <option>All Stores</option>
              {activeStores.map((item) => (
                <option key={item.id}>{item.name}</option>
              ))}
            </select>
          </label>
        }
      />
      {feedback && (
        <div className="success-banner">
          <CheckCircle2 size={19} />
          <span>{feedback}</span>
          <button aria-label="Dismiss replenishment confirmation" onClick={() => setFeedback("")}>
            <X size={17} />
          </button>
        </div>
      )}
      <section className="replenishment-summary">
        <div>
          <span>Needs replenishment</span>
          <strong>{sorted.length}</strong>
          <small>Store-level records</small>
        </div>
        <div className="critical">
          <span>Out of stock</span>
          <strong>{out.length}</strong>
          <small>Resolve first</small>
        </div>
        <div className="warning">
          <span>Below reorder</span>
          <strong>{low.length}</strong>
          <small>Restore next</small>
        </div>
        <p>
          <Sparkles size={18} />
          <span>
            <strong>Target rule</strong>Restock to twice the reorder level. No forecasting or hidden
            score.
          </span>
        </p>
      </section>
      <section className="data-surface replenishment-table">
        <div className="queue-heading">
          <span>
            <ShieldAlert size={18} />
            Priority queue
          </span>
          <small>Out-of-stock items always appear first.</small>
        </div>
        <QueueGroup title="Out of stock" tone="critical" rows={out} onRestock={setRestock} />
        <QueueGroup title="Below reorder level" tone="warning" rows={low} onRestock={setRestock} />
        {!sorted.length && (
          <EmptyState
            icon={BadgeCheck}
            title="This store is fully stocked"
            text="No balances are at or below their reorder level."
          />
        )}
      </section>
      {restock && (
        <MovementDialog
          initialRow={restock}
          initialMode="Restock"
          onClose={() => setRestock(null)}
          onComplete={(message) => {
            setFeedback(message);
            setRestock(null);
          }}
        />
      )}
    </>
  );
}

function QueueGroup({
  title,
  tone,
  rows,
  onRestock,
}: {
  title: string;
  tone: string;
  rows: InventoryRow[];
  onRestock: (row: InventoryRow) => void;
}) {
  if (!rows.length) return null;
  return (
    <div className="queue-group">
      <div className={`queue-group-title ${tone}`}>
        <span>
          <i />
          {title}
        </span>
        <b>{rows.length}</b>
      </div>
      <div className="desktop-table">
        <table>
          <thead>
            <tr>
              <th>Priority</th>
              <th>Product</th>
              <th>SKU</th>
              <th>Store</th>
              <th>Current</th>
              <th>Reorder</th>
              <th>Suggested restock</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => {
              const suggested = row.reorder * 2 - row.quantity;
              return (
                <tr key={row.id}>
                  <td>
                    <span className={`priority-marker ${tone}`}>
                      <b>{String(index + 1).padStart(2, "0")}</b>
                      <span>{tone === "critical" ? "Immediate" : "Next"}</span>
                    </span>
                  </td>
                  <td>
                    <strong>{row.name}</strong>
                  </td>
                  <td className="mono">{row.sku}</td>
                  <td>{row.store}</td>
                  <td className={`numeric ${tone === "critical" ? "negative" : "warning-text"}`}>
                    <strong>{row.quantity}</strong>
                  </td>
                  <td className="numeric">{row.reorder}</td>
                  <td>
                    <span className="suggested">
                      <strong>+{suggested}</strong>
                      <small>to {row.reorder * 2} units</small>
                    </span>
                  </td>
                  <td>
                    <Button
                      variant="secondary"
                      icon={ArrowDownToLine}
                      onClick={() => onRestock(row)}
                    >
                      Restock
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="mobile-records">
        {rows.map((row, index) => {
          const suggested = row.reorder * 2 - row.quantity;
          return (
            <article className="mobile-card replenishment-card" key={row.id}>
              <span className={`priority-number ${tone}`}>
                {String(index + 1).padStart(2, "0")}
              </span>
              <div>
                <strong>{row.name}</strong>
                <span>
                  {row.sku} · {row.store}
                </span>
                <p>
                  <b>{row.quantity}</b> now · <b>{row.reorder}</b> reorder ·{" "}
                  <strong>+{suggested}</strong> suggested
                </p>
              </div>
              <Button icon={ArrowDownToLine} onClick={() => onRestock(row)}>
                Restock
              </Button>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function EmptyState({
  icon: Icon,
  title,
  text,
  action,
}: {
  icon: LucideIcon;
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <span>
        <Icon size={24} />
      </span>
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </div>
  );
}

function NotFound() {
  return (
    <div className="not-found">
      <Boxes size={34} />
      <h1>Workspace not found</h1>
      <p>Return to StockFlow’s operational overview.</p>
      <Link className="button primary" to="/overview">
        Go to Overview
      </Link>
    </div>
  );
}

export const router = createBrowserRouter([
  {
    path: "/",
    Component: AppShell,
    children: [
      { index: true, element: <Navigate to="/overview" replace /> },
      { path: "overview", Component: Overview },
      { path: "catalogue", Component: Catalogue },
      { path: "inventory", Component: Inventory },
      { path: "replenishment", Component: Replenishment },
      { path: "import", Component: ImportStudio },
      { path: "*", Component: NotFound },
    ],
  },
]);
