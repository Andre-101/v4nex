import { FormEvent, useEffect, useMemo, useState } from "react"

type BridgeStatus = "DRAFT" | "VALIDATING" | "READY" | "ACTIVE" | "ERROR" | "DISABLED" | "SUSPENDED"
type View = "overview" | "bridges" | "detail" | "new" | "edit" | "admin"
type AdminView = "users" | "bridges"

type Bridge = {
  id: string
  subdomain: string
  public_url: string
  target_ipv6: string
  target_port: number
  status: BridgeStatus
  last_tcp_validation_result?: string | null
  last_heartbeat_result?: string | null
}

type CurrentUser = {
  id: string
  email: string
  role: "USER" | "ADMIN"
  bridge_limit: number
  is_active: boolean
  bridges_used: number
}

type AdminUser = {
  id: string
  email: string
  role: "USER" | "ADMIN"
  is_active: boolean
  bridge_limit: number
  bridges_used: number
  created_at: string
  updated_at: string
}

type AdminBridge = Bridge & {
  user_id: string
  owner_email: string
}

type ApiError = {
  error?: {
    code?: string
    message?: string
    details?: Record<string, unknown>
  }
}

type BridgeForm = {
  subdomain: string
  target_ipv6: string
  target_port: number
}

const endpoints = {
  register: "/_v4nex/auth/register",
  login: "/_v4nex/auth/login",
  me: "/_v4nex/auth/me",
  bridges: "/_v4nex/bridges",
  adminUsers: "/_v4nex/admin/users",
  adminBridges: "/_v4nex/admin/bridges",
}

const allowedPorts = [80, 8080]
const emptyForm: BridgeForm = { subdomain: "", target_ipv6: "", target_port: 80 }

class SessionExpiredError extends Error {}

function isPreviewAllowed() {
  if (typeof window === "undefined") return false
  const host = window.location.hostname
  return [String.raw`local` + String.raw`host`, "127.0.0.1", "::1"].includes(host)
}

function isBridgeHostWithoutPanel() {
  if (typeof window === "undefined") return false
  const host = window.location.hostname.toLowerCase()
  if (host === "v4nex.com" || isPreviewAllowed()) return false
  return host.endsWith(".v4nex.com")
}

function isPreviewSession() {
  return isPreviewAllowed() && sessionStorage.getItem("v4nex_preview_session") === "true"
}

function getInitialToken() {
  return isPreviewSession() ? "local-preview-token" : sessionStorage.getItem("v4nex_access_token") ?? ""
}

function getInitialEmail() {
  return isPreviewSession() ? "preview@v4nex.local" : sessionStorage.getItem("v4nex_user_email") ?? ""
}

function getPreviewBridges(): Bridge[] {
  if (!isPreviewAllowed()) return []
  return [
    {
      id: "preview-draft",
      subdomain: "preview",
      public_url: "https://preview.v4nex.com",
      target_ipv6: "2606:4700:4700::1111",
      target_port: 80,
      status: "DRAFT",
      last_tcp_validation_result: null,
    },
  ]
}

function getPreviewUser(): CurrentUser {
  const bridges = getPreviewBridges()
  return {
    id: "preview-user",
    email: "preview@v4nex.local",
    role: "ADMIN",
    bridge_limit: 3,
    is_active: true,
    bridges_used: bridges.length,
  }
}

function isNetworkError(error: unknown) {
  return error instanceof TypeError
}

function networkErrorMessage() {
  if (isPreviewAllowed()) {
    return "No pudimos conectar con la API. Inicia el backend local o usa Vista previa del panel."
  }
  return "No pudimos conectar con la API. Intenta de nuevo en unos minutos."
}

function allowedPortsMessage(details?: Record<string, unknown>) {
  const ports = details?.allowed_ports
  if (Array.isArray(ports) && ports.length > 0) {
    return ` Puertos permitidos: ${ports.join(", ")}.`
  }
  return ""
}

function friendlyError(error: ApiError, fallback: string) {
  const code = error.error?.code
  if (code === "INVALID_PORT") {
    return "Este puerto no está permitido. Actualmente se permiten 80 y 8080."
  }
  if (code === "TCP_VALIDATION_FAILED") {
    return "No se pudo conectar al destino IPv6. Verifica dirección, puerto, firewall y que el servicio esté escuchando."
  }
  if (code === "INVALID_STATE_TRANSITION") {
    return error.error?.message?.toLowerCase().includes("deleting")
      ? "Este bridge está activo. Desactívalo antes de eliminarlo."
      : "Este bridge está activo. Desactívalo antes de editarlo."
  }
  return `${fallback}${allowedPortsMessage(error.error?.details)}`
}

async function parseResponse<T>(response: Response, fallback: string): Promise<T> {
  const body = (await response.json().catch(() => ({}))) as ApiError
  if (response.status === 401) {
    throw new SessionExpiredError("Tu sesión expiró. Inicia sesión nuevamente.")
  }
  if (!response.ok) {
    throw new Error(friendlyError(body, fallback))
  }
  return body as T
}

function statusLabel(status: BridgeStatus) {
  const labels: Record<BridgeStatus, string> = {
    DRAFT: "BORRADOR",
    VALIDATING: "VALIDANDO",
    READY: "LISTO",
    ACTIVE: "ACTIVO",
    ERROR: "ERROR",
    DISABLED: "DESACTIVADO",
    SUSPENDED: "SUSPENDIDO",
  }
  return labels[status] ?? status
}

function canEdit(status: BridgeStatus) {
  return ["DRAFT", "READY", "DISABLED", "ERROR"].includes(status)
}

function canDelete(status: BridgeStatus) {
  return canEdit(status)
}

function canValidate(status: BridgeStatus) {
  return ["DRAFT", "ERROR", "DISABLED"].includes(status)
}

function canActivate(status: BridgeStatus) {
  return status === "READY"
}

function canDisable(status: BridgeStatus) {
  return status === "ACTIVE"
}

function BridgeNotFoundPage() {
  return (
    <main className="app">
      <section className="panel">
        <h1>Bridge no encontrado</h1>
        <p>Este subdominio no tiene un bridge activo o el servicio fue desactivado.</p>
        <a className="button-link" href="https://v4nex.com">
          Ir a v4nex
        </a>
      </section>
    </main>
  )
}

function App() {
  const [token, setToken] = useState(getInitialToken)
  const [email, setEmail] = useState(getInitialEmail)
  const [isPreview, setIsPreview] = useState(isPreviewSession)
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(isPreviewSession() ? getPreviewUser() : null)
  const [authMode, setAuthMode] = useState<"login" | "register">("login")
  const [authEmail, setAuthEmail] = useState("")
  const [password, setPassword] = useState("")
  const [authMessage, setAuthMessage] = useState("")
  const [authError, setAuthError] = useState("")
  const [view, setView] = useState<View>("overview")
  const [bridges, setBridges] = useState<Bridge[]>(isPreviewSession() ? getPreviewBridges() : [])
  const [selectedBridgeId, setSelectedBridgeId] = useState("")
  const [bridgeForm, setBridgeForm] = useState<BridgeForm>(emptyForm)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  const [runningActionId, setRunningActionId] = useState("")
  const [adminView, setAdminView] = useState<AdminView>("users")
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([])
  const [adminBridges, setAdminBridges] = useState<AdminBridge[]>([])

  const isAuthenticated = Boolean(token)
  const isAdmin = currentUser?.role === "ADMIN"
  const bridgeLimitReached = Boolean(currentUser && currentUser.bridges_used >= currentUser.bridge_limit)
  const selectedBridge = bridges.find((bridge) => bridge.id === selectedBridgeId) ?? null
  const totals = useMemo(
    () => ({
      total: bridges.length,
      ready: bridges.filter((bridge) => bridge.status === "READY").length,
      active: bridges.filter((bridge) => bridge.status === "ACTIVE").length,
    }),
    [bridges],
  )

  function clearNotices() {
    setMessage("")
    setError("")
  }

  function handleSessionExpired(errorValue: unknown) {
    if (!(errorValue instanceof SessionExpiredError)) return false
    logout()
    setAuthError("Tu sesión expiró. Inicia sesión nuevamente.")
    return true
  }

  async function loadCurrentUser() {
    if (!token) return null
    if (isPreview) {
      const previewUser = { ...getPreviewUser(), bridges_used: bridges.length }
      setCurrentUser(previewUser)
      return previewUser
    }

    const data = await parseResponse<CurrentUser>(
      await fetch(endpoints.me, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      "No pudimos cargar tu sesiÃ³n.",
    )
    setCurrentUser(data)
    setEmail(data.email)
    return data
  }

  async function loadBridges() {
    if (!token) return
    if (isPreview) {
      setCurrentUser((user) => (user ? { ...user, bridges_used: bridges.length } : getPreviewUser()))
      return
    }

    setLoading(true)
    setError("")
    try {
      const data = await parseResponse<Bridge[]>(
        await fetch(endpoints.bridges, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        "No pudimos cargar los bridges.",
      )
      setBridges(data)
      setCurrentUser((user) => (user ? { ...user, bridges_used: data.length } : user))
    } catch (errorValue) {
      if (handleSessionExpired(errorValue)) return
      setError(isNetworkError(errorValue) ? networkErrorMessage() : "No pudimos cargar los bridges.")
    } finally {
      setLoading(false)
    }
  }

  async function loadBridgeDetail(bridgeId: string) {
    if (!token || isPreview) return bridges.find((bridge) => bridge.id === bridgeId) ?? null

    const data = await parseResponse<Bridge>(
      await fetch(`${endpoints.bridges}/${bridgeId}`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      "No pudimos cargar el detalle del bridge.",
    )
    setBridges((current) => current.map((bridge) => (bridge.id === data.id ? data : bridge)))
    return data
  }

  async function loadAdminData() {
    if (!token || !isAdmin) return
    if (isPreview) {
      setAdminUsers([
        { ...getPreviewUser(), created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
      ])
      setAdminBridges(
        bridges.map((bridge) => ({
          ...bridge,
          user_id: "preview-user",
          owner_email: "preview@v4nex.local",
        })),
      )
      return
    }

    const [users, globalBridges] = await Promise.all([
      parseResponse<AdminUser[]>(
        await fetch(endpoints.adminUsers, { headers: { Authorization: `Bearer ${token}` } }),
        "No pudimos cargar usuarios.",
      ),
      parseResponse<AdminBridge[]>(
        await fetch(endpoints.adminBridges, { headers: { Authorization: `Bearer ${token}` } }),
        "No pudimos cargar bridges globales.",
      ),
    ])
    setAdminUsers(users)
    setAdminBridges(globalBridges)
  }

  useEffect(() => {
    if (!token) return
    void loadCurrentUser()
      .then(() => loadBridges())
      .catch((errorValue) => {
        if (handleSessionExpired(errorValue)) return
        setError(isNetworkError(errorValue) ? networkErrorMessage() : "No pudimos cargar tu sesiÃ³n.")
      })
  }, [token, isPreview])

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAuthError("")
    setAuthMessage("")

    try {
      if (authMode === "register") {
        await parseResponse<{ id: string; email: string }>(
          await fetch(endpoints.register, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: authEmail, password }),
          }),
          "No pudimos crear la cuenta. Verifica el correo y la contraseña.",
        )
        setAuthMessage("Cuenta creada. Ahora puedes entrar.")
        setAuthMode("login")
        setPassword("")
        return
      }

      const data = await parseResponse<{ access_token: string; token_type: string }>(
        await fetch(endpoints.login, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: authEmail, password }),
        }),
        "No pudimos iniciar sesión. Revisa tus credenciales o crea una cuenta nueva.",
      )
      sessionStorage.setItem("v4nex_access_token", data.access_token)
      sessionStorage.setItem("v4nex_user_email", authEmail)
      sessionStorage.removeItem("v4nex_preview_session")
      setToken(data.access_token)
      setEmail(authEmail)
      setCurrentUser(null)
      setIsPreview(false)
      setPassword("")
      setView("overview")
    } catch (errorValue) {
      if (isNetworkError(errorValue)) {
        setAuthError(networkErrorMessage())
        return
      }
      setAuthError(errorValue instanceof Error ? errorValue.message : "No pudimos completar la autenticación.")
    }
  }

  function startPreview() {
    if (!isPreviewAllowed()) return
    sessionStorage.setItem("v4nex_preview_session", "true")
    sessionStorage.removeItem("v4nex_access_token")
    sessionStorage.removeItem("v4nex_user_email")
    setToken("local-preview-token")
    setEmail("preview@v4nex.local")
    setCurrentUser(getPreviewUser())
    setIsPreview(true)
    setBridges(getPreviewBridges())
    setView("overview")
    setAuthError("")
    setAuthMessage("")
  }

  function logout() {
    sessionStorage.removeItem("v4nex_access_token")
    sessionStorage.removeItem("v4nex_user_email")
    sessionStorage.removeItem("v4nex_preview_session")
    setToken("")
    setEmail("")
    setCurrentUser(null)
    setIsPreview(false)
    setBridges([])
    setAdminUsers([])
    setAdminBridges([])
    setSelectedBridgeId("")
    setBridgeForm(emptyForm)
    setView("overview")
    setMessage("")
    setError("")
  }

  function openDetail(bridge: Bridge) {
    clearNotices()
    setSelectedBridgeId(bridge.id)
    setView("detail")
    void loadBridgeDetail(bridge.id).catch((errorValue) => {
      if (handleSessionExpired(errorValue)) return
      setError(errorValue instanceof Error ? errorValue.message : "No pudimos cargar el detalle.")
    })
  }

  function openEdit(bridge: Bridge) {
    clearNotices()
    if (!canEdit(bridge.status)) {
      setError("Este bridge está activo. Desactívalo antes de editarlo.")
      return
    }
    setSelectedBridgeId(bridge.id)
    setBridgeForm({
      subdomain: bridge.subdomain,
      target_ipv6: bridge.target_ipv6,
      target_port: bridge.target_port,
    })
    setView("edit")
  }

  function openNew() {
    clearNotices()
    if (bridgeLimitReached) {
      setError("Alcanzaste el lÃ­mite de bridges de tu cuenta.")
      return
    }
    setBridgeForm(emptyForm)
    setView("new")
  }

  async function submitBridge(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    clearNotices()

    if (!allowedPorts.includes(bridgeForm.target_port)) {
      setError("Este puerto no está permitido. Actualmente se permiten 80 y 8080.")
      return
    }

    if (bridgeLimitReached) {
      setError("Alcanzaste el limite de bridges de tu cuenta.")
      return
    }

    if (isPreview) {
      const previewBridge: Bridge = {
        id: `preview-${Date.now()}`,
        subdomain: bridgeForm.subdomain,
        public_url: `https://${bridgeForm.subdomain}.v4nex.com`,
        target_ipv6: bridgeForm.target_ipv6,
        target_port: bridgeForm.target_port,
        status: "DRAFT",
        last_tcp_validation_result: null,
      }
      setBridges((current) => [previewBridge, ...current])
      setBridgeForm(emptyForm)
      setView("bridges")
      setMessage("Bridge creado en estado DRAFT.")
      return
    }

    try {
      await parseResponse<Bridge>(
        await fetch(endpoints.bridges, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(bridgeForm),
        }),
        "No pudimos crear el bridge. Revisa el subdominio, la IPv6 y el puerto permitido.",
      )
      setBridgeForm(emptyForm)
      setView("bridges")
      setMessage("Bridge creado en estado DRAFT.")
      await loadBridges()
    } catch (errorValue) {
      if (handleSessionExpired(errorValue)) return
      setError(isNetworkError(errorValue) ? networkErrorMessage() : errorValue instanceof Error ? errorValue.message : "No pudimos crear el bridge.")
    }
  }

  async function submitBridgeEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    clearNotices()
    if (!selectedBridge) return
    if (!canEdit(selectedBridge.status)) {
      setError("Este bridge está activo. Desactívalo antes de editarlo.")
      return
    }
    if (!allowedPorts.includes(bridgeForm.target_port)) {
      setError("Este puerto no está permitido. Actualmente se permiten 80 y 8080.")
      return
    }

    if (isPreview) {
      setBridges((current) =>
        current.map((bridge) =>
          bridge.id === selectedBridge.id
            ? {
                ...bridge,
                subdomain: bridgeForm.subdomain,
                public_url: `https://${bridgeForm.subdomain}.v4nex.com`,
                target_ipv6: bridgeForm.target_ipv6,
                target_port: bridgeForm.target_port,
                status: "DRAFT",
                last_tcp_validation_result: null,
              }
            : bridge,
        ),
      )
      setView("bridges")
      setMessage("Bridge actualizado y devuelto a DRAFT.")
      return
    }

    try {
      const data = await parseResponse<Bridge>(
        await fetch(`${endpoints.bridges}/${selectedBridge.id}`, {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(bridgeForm),
        }),
        "No pudimos actualizar el bridge. Revisa el subdominio, la IPv6 y el puerto permitido.",
      )
      setBridges((current) => current.map((bridge) => (bridge.id === data.id ? data : bridge)))
      setView("detail")
      setMessage("Bridge actualizado y devuelto a DRAFT.")
      await loadBridges()
    } catch (errorValue) {
      if (handleSessionExpired(errorValue)) return
      setError(isNetworkError(errorValue) ? networkErrorMessage() : errorValue instanceof Error ? errorValue.message : "No pudimos actualizar el bridge.")
    }
  }

  async function runBridgeAction(bridge: Bridge, action: "validate" | "activate" | "disable") {
    clearNotices()
    setRunningActionId(`${bridge.id}:${action}`)

    if (isPreview) {
      setBridges((current) =>
        current.map((currentBridge) => {
          if (currentBridge.id !== bridge.id) return currentBridge
          if (action === "validate") {
            return { ...currentBridge, status: "READY", last_tcp_validation_result: "OK" }
          }
          if (action === "activate") {
            return { ...currentBridge, status: "ACTIVE" }
          }
          return { ...currentBridge, status: "DISABLED" }
        }),
      )
      setMessage(actionSuccessMessage(action))
      setRunningActionId("")
      return
    }

    try {
      await parseResponse<Bridge>(
        await fetch(`${endpoints.bridges}/${bridge.id}/${action}`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }),
        actionFallbackMessage(action),
      )
      setMessage(actionSuccessMessage(action))
      await loadBridges()
      await loadBridgeDetail(bridge.id)
    } catch (errorValue) {
      if (handleSessionExpired(errorValue)) return
      setError(isNetworkError(errorValue) ? networkErrorMessage() : errorValue instanceof Error ? errorValue.message : "No pudimos completar la acción.")
      await loadBridges()
    } finally {
      setRunningActionId("")
    }
  }

  async function deleteBridge(bridge: Bridge) {
    clearNotices()
    if (!canDelete(bridge.status)) {
      setError("Este bridge está activo. Desactívalo antes de eliminarlo.")
      return
    }
    setRunningActionId(`${bridge.id}:delete`)

    if (isPreview) {
      setBridges((current) => current.filter((currentBridge) => currentBridge.id !== bridge.id))
      setSelectedBridgeId("")
      setView("bridges")
      setMessage("El bridge fue eliminado.")
      setRunningActionId("")
      return
    }

    try {
      const response = await fetch(`${endpoints.bridges}/${bridge.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.status === 401) throw new SessionExpiredError("Tu sesión expiró. Inicia sesión nuevamente.")
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as ApiError
        throw new Error(friendlyError(body, "No pudimos eliminar el bridge."))
      }
      setSelectedBridgeId("")
      setView("bridges")
      setMessage("El bridge fue eliminado.")
      await loadBridges()
    } catch (errorValue) {
      if (handleSessionExpired(errorValue)) return
      setError(isNetworkError(errorValue) ? networkErrorMessage() : errorValue instanceof Error ? errorValue.message : "No pudimos eliminar el bridge.")
    } finally {
      setRunningActionId("")
    }
  }

  function actionSuccessMessage(action: "validate" | "activate" | "disable") {
    if (action === "validate") return "El servicio IPv6 respondió correctamente. El bridge quedó listo para activarse."
    if (action === "activate") return "El bridge fue activado. La URL pública ya debería responder."
    return "El bridge fue desactivado. La ruta pública dejó de apuntar al destino IPv6."
  }

  function actionFallbackMessage(action: "validate" | "activate" | "disable") {
    if (action === "validate") return "No se pudo conectar al destino IPv6. Verifica dirección, puerto, firewall y que el servicio esté escuchando."
    if (action === "activate") return "No pudimos activar el bridge."
    return "No pudimos desactivar el bridge."
  }

  async function adminPatchUser(user: AdminUser, payload: Partial<Pick<AdminUser, "bridge_limit" | "is_active">>) {
    clearNotices()
    if (isPreview) {
      setAdminUsers((current) => current.map((item) => (item.id === user.id ? { ...item, ...payload } : item)))
      setMessage("Usuario actualizado.")
      return
    }
    try {
      await parseResponse<AdminUser>(
        await fetch(`${endpoints.adminUsers}/${user.id}`, {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }),
        "No pudimos actualizar el usuario.",
      )
      setMessage("Usuario actualizado.")
      await loadAdminData()
    } catch (errorValue) {
      if (handleSessionExpired(errorValue)) return
      setError(errorValue instanceof Error ? errorValue.message : "No pudimos actualizar el usuario.")
    }
  }

  async function adminDeleteUser(user: AdminUser) {
    clearNotices()
    if (isPreview) {
      setAdminUsers((current) => current.filter((item) => item.id !== user.id))
      setMessage("Usuario eliminado.")
      return
    }
    try {
      const response = await fetch(`${endpoints.adminUsers}/${user.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.status === 401) throw new SessionExpiredError("Tu sesión expiró. Inicia sesión nuevamente.")
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as ApiError
        throw new Error(friendlyError(body, "No pudimos eliminar el usuario."))
      }
      setMessage("Usuario eliminado.")
      await loadAdminData()
    } catch (errorValue) {
      if (handleSessionExpired(errorValue)) return
      setError(errorValue instanceof Error ? errorValue.message : "No pudimos eliminar el usuario.")
    }
  }

  async function adminBridgeAction(bridge: AdminBridge, action: "disable" | "delete") {
    clearNotices()
    if (isPreview) {
      setAdminBridges((current) =>
        action === "delete"
          ? current.filter((item) => item.id !== bridge.id)
          : current.map((item) => (item.id === bridge.id ? { ...item, status: "DISABLED" } : item)),
      )
      setMessage(action === "delete" ? "Bridge eliminado." : "Bridge desactivado.")
      return
    }
    try {
      const response = await fetch(`${endpoints.adminBridges}/${bridge.id}${action === "disable" ? "/disable" : ""}`, {
        method: action === "disable" ? "POST" : "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (response.status === 401) throw new SessionExpiredError("Tu sesión expiró. Inicia sesión nuevamente.")
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as ApiError
        throw new Error(friendlyError(body, action === "delete" ? "No pudimos eliminar el bridge." : "No pudimos desactivar el bridge."))
      }
      setMessage(action === "delete" ? "Bridge eliminado." : "Bridge desactivado.")
      await loadAdminData()
      await loadBridges()
    } catch (errorValue) {
      if (handleSessionExpired(errorValue)) return
      setError(errorValue instanceof Error ? errorValue.message : "No pudimos completar la acción admin.")
    }
  }

  function renderActions(bridge: Bridge) {
    return (
      <div className="actions">
        <button className="secondary" type="button" onClick={() => openDetail(bridge)}>
          Ver
        </button>
        {canEdit(bridge.status) && (
          <button className="secondary" type="button" onClick={() => openEdit(bridge)}>
            Editar
          </button>
        )}
        {canValidate(bridge.status) && (
          <button type="button" disabled={runningActionId === `${bridge.id}:validate`} onClick={() => void runBridgeAction(bridge, "validate")}>
            Validar
          </button>
        )}
        {canActivate(bridge.status) && (
          <button type="button" disabled={runningActionId === `${bridge.id}:activate`} onClick={() => void runBridgeAction(bridge, "activate")}>
            Activar
          </button>
        )}
        {canDisable(bridge.status) && (
          <button type="button" disabled={runningActionId === `${bridge.id}:disable`} onClick={() => void runBridgeAction(bridge, "disable")}>
            Desactivar
          </button>
        )}
        {bridge.status === "ACTIVE" && (
          <a className="button-link" href={bridge.public_url} target="_blank" rel="noreferrer">
            Abrir URL
          </a>
        )}
        {canDelete(bridge.status) && (
          <button className="danger" type="button" disabled={runningActionId === `${bridge.id}:delete`} onClick={() => void deleteBridge(bridge)}>
            Eliminar
          </button>
        )}
      </div>
    )
  }

  function renderBridgeForm(onSubmit: (event: FormEvent<HTMLFormElement>) => void, submitText: string) {
    return (
      <form onSubmit={onSubmit}>
        <label>
          Subdominio
          <input value={bridgeForm.subdomain} onChange={(event) => setBridgeForm({ ...bridgeForm, subdomain: event.target.value })} required />
        </label>
        <label>
          IPv6 destino
          <input value={bridgeForm.target_ipv6} onChange={(event) => setBridgeForm({ ...bridgeForm, target_ipv6: event.target.value })} required />
        </label>
        <label>
          Puerto destino
          <select value={bridgeForm.target_port} onChange={(event) => setBridgeForm({ ...bridgeForm, target_port: Number(event.target.value) })}>
            <option value={80}>80 - HTTP</option>
            <option value={8080}>8080 - HTTP alternativo</option>
          </select>
        </label>
        <button type="submit">{submitText}</button>
      </form>
    )
  }

  if (isBridgeHostWithoutPanel()) {
    return <BridgeNotFoundPage />
  }

  if (!isAuthenticated) {
    return (
      <main className="app">
        <section className="panel">
          <h1>v4nex</h1>
          <p className="muted">Edge Connectivity. Limitless Access.</p>
          <p>Publica servicios IPv6 detrás de una entrada IPv4 con dominios, TLS y reverse proxy L7.</p>
        </section>

        <section className="panel">
          <div className="tabs">
            <button className={authMode === "login" ? "active" : ""} type="button" onClick={() => setAuthMode("login")}>
              Entrar
            </button>
            <button className={authMode === "register" ? "active" : ""} type="button" onClick={() => setAuthMode("register")}>
              Crear cuenta
            </button>
          </div>

          <form onSubmit={submitAuth}>
            <label>
              Email
              <input type="email" value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} required />
            </label>
            <label>
              Contraseña
              <input type="password" value={password} minLength={8} onChange={(event) => setPassword(event.target.value)} required />
            </label>
            <button type="submit">{authMode === "login" ? "Entrar" : "Crear cuenta"}</button>
          </form>

          {authMessage && <p className="success">{authMessage}</p>}
          {authError && <p className="error">{authError}</p>}

          {isPreviewAllowed() && (
            <button className="secondary" type="button" onClick={startPreview}>
              Vista previa del panel
            </button>
          )}
        </section>
      </main>
    )
  }

  return (
    <main className="app app-wide">
      <header className="topbar">
        <div>
          <h1>v4nex</h1>
          <p className="muted">{email}</p>
          {isPreview && <p className="notice">Vista previa local. No llama al backend.</p>}
        </div>
        <button className="secondary" type="button" onClick={logout}>
          Cerrar sesión
        </button>
      </header>

      <nav className="nav">
        <button className={view === "overview" ? "active" : ""} type="button" onClick={() => setView("overview")}>
          Resumen
        </button>
        <button className={view === "bridges" ? "active" : ""} type="button" onClick={() => setView("bridges")}>
          Bridges
        </button>
        <button className={view === "new" ? "active" : ""} type="button" onClick={openNew} disabled={bridgeLimitReached}>
          Nuevo bridge
        </button>
        {isAdmin && (
          <button
            className={view === "admin" ? "active" : ""}
            type="button"
            onClick={() => {
              setView("admin")
              void loadAdminData().catch((errorValue) => {
                if (handleSessionExpired(errorValue)) return
                setError(errorValue instanceof Error ? errorValue.message : "No pudimos cargar Admin.")
              })
            }}
          >
            Admin
          </button>
        )}
      </nav>

      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}

      {view === "overview" && (
        <section className="grid">
          <div className="panel">
            <h2>Bridges totales</h2>
            <p className="metric">{totals.total}</p>
          </div>
          <div className="panel">
            <h2>Listos</h2>
            <p className="metric">{totals.ready}</p>
          </div>
          <div className="panel">
            <h2>Activos</h2>
            <p className="metric">{totals.active}</p>
          </div>
          <div className="panel">
            <h2>Cupo de bridges</h2>
            <p className="metric">
              {currentUser?.bridges_used ?? bridges.length}/{currentUser?.bridge_limit ?? "-"}
            </p>
            {currentUser?.bridge_limit === 0 && <p className="error">Tu cuenta no tiene cupo disponible para crear bridges.</p>}
            {currentUser && currentUser.bridge_limit > 0 && currentUser.bridges_used >= currentUser.bridge_limit && (
              <p className="notice">Alcanzaste el limite de bridges de tu cuenta.</p>
            )}
          </div>
          <div className="panel">
            <h2>Estado operacional</h2>
            <p>API autenticada conectada.</p>
            <p>Las rutas públicas solo son utilizables cuando el bridge está ACTIVO.</p>
          </div>
        </section>
      )}

      {view === "bridges" && (
        <section className="panel">
          <div className="section-header">
            <h2>Bridges</h2>
            <div className="actions">
              <button className="secondary" type="button" onClick={() => void loadBridges()} disabled={loading || isPreview}>
                {loading ? "Actualizando..." : "Actualizar"}
              </button>
              <button type="button" onClick={openNew} disabled={bridgeLimitReached}>
                Nuevo bridge
              </button>
            </div>
          </div>

          {bridges.length === 0 ? (
            <p className="muted">Aún no tienes bridges configurados.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Subdominio</th>
                    <th>URL pública</th>
                    <th>IPv6 destino</th>
                    <th>Puerto</th>
                    <th>Estado</th>
                    <th>Validación TCP</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {bridges.map((bridge) => (
                    <tr key={bridge.id}>
                      <td>{bridge.subdomain}</td>
                      <td>
                        {bridge.status === "ACTIVE" ? (
                          <a href={bridge.public_url} target="_blank" rel="noreferrer">
                            {bridge.public_url}
                          </a>
                        ) : (
                          bridge.public_url
                        )}
                      </td>
                      <td>{bridge.target_ipv6}</td>
                      <td>{bridge.target_port}</td>
                      <td>{statusLabel(bridge.status)}</td>
                      <td>{bridge.last_tcp_validation_result ?? "-"}</td>
                      <td>{renderActions(bridge)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {view === "new" && (
        <section className="panel narrow">
          <h2>Nuevo bridge</h2>
          <p className="muted">Crea un bridge en estado DRAFT. Valida y activa cuando el destino IPv6 esté listo.</p>
          {renderBridgeForm(submitBridge, "Crear bridge")}
        </section>
      )}

      {view === "edit" && selectedBridge && (
        <section className="panel narrow">
          <h2>Editar bridge</h2>
          <p className="muted">Editar subdominio, IPv6 o puerto devuelve el bridge a DRAFT.</p>
          {renderBridgeForm(submitBridgeEdit, "Guardar cambios")}
        </section>
      )}

      {view === "admin" && isAdmin && (
        <section className="panel">
          <div className="section-header">
            <div>
              <h2>Admin</h2>
              <p className="muted">Gestión operativa de usuarios, cuotas y bridges.</p>
            </div>
            <div className="actions">
              <button className={adminView === "users" ? "active" : "secondary"} type="button" onClick={() => setAdminView("users")}>
                Usuarios
              </button>
              <button className={adminView === "bridges" ? "active" : "secondary"} type="button" onClick={() => setAdminView("bridges")}>
                Bridges globales
              </button>
              <button className="secondary" type="button" onClick={() => void loadAdminData()}>
                Actualizar
              </button>
            </div>
          </div>

          {adminView === "users" && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Rol</th>
                    <th>Estado</th>
                    <th>Bridges</th>
                    <th>Límite</th>
                    <th>Creado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {adminUsers.map((user) => (
                    <tr key={user.id}>
                      <td>{user.email}</td>
                      <td>{user.role}</td>
                      <td>{user.is_active ? "Activo" : "Suspendido"}</td>
                      <td>{user.bridges_used}</td>
                      <td>{user.bridge_limit}</td>
                      <td>{new Date(user.created_at).toLocaleDateString()}</td>
                      <td>
                        <div className="actions">
                          <button type="button" onClick={() => void adminPatchUser(user, { bridge_limit: Math.max(0, user.bridge_limit + 1) })}>
                            +1 límite
                          </button>
                          <button className="secondary" type="button" onClick={() => void adminPatchUser(user, { bridge_limit: 0 })}>
                            Límite 0
                          </button>
                          {user.is_active ? (
                            <button className="danger" type="button" onClick={() => void adminPatchUser(user, { is_active: false })}>
                              Suspender
                            </button>
                          ) : (
                            <button type="button" onClick={() => void adminPatchUser(user, { is_active: true })}>
                              Reactivar
                            </button>
                          )}
                          <button className="danger" type="button" onClick={() => void adminDeleteUser(user)}>
                            Eliminar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {adminView === "bridges" && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Subdominio</th>
                    <th>Estado</th>
                    <th>IPv6 destino</th>
                    <th>Puerto</th>
                    <th>Owner</th>
                    <th>URL pública</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {adminBridges.map((bridge) => (
                    <tr key={bridge.id}>
                      <td>{bridge.subdomain}</td>
                      <td>{statusLabel(bridge.status)}</td>
                      <td>{bridge.target_ipv6}</td>
                      <td>{bridge.target_port}</td>
                      <td>{bridge.owner_email}</td>
                      <td>{bridge.public_url}</td>
                      <td>
                        <div className="actions">
                          {bridge.status === "ACTIVE" && (
                            <button type="button" onClick={() => void adminBridgeAction(bridge, "disable")}>
                              Desactivar
                            </button>
                          )}
                          {bridge.status !== "ACTIVE" && (
                            <button className="danger" type="button" onClick={() => void adminBridgeAction(bridge, "delete")}>
                              Eliminar
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {view === "detail" && selectedBridge && (
        <section className="panel">
          <div className="section-header">
            <h2>Detalle de bridge</h2>
            {renderActions(selectedBridge)}
          </div>
          <dl className="details">
            <dt>ID</dt>
            <dd>{selectedBridge.id}</dd>
            <dt>Subdominio</dt>
            <dd>{selectedBridge.subdomain}</dd>
            <dt>URL pública</dt>
            <dd>
              {selectedBridge.status === "ACTIVE" ? (
                <a href={selectedBridge.public_url} target="_blank" rel="noreferrer">
                  {selectedBridge.public_url}
                </a>
              ) : (
                selectedBridge.public_url
              )}
            </dd>
            <dt>IPv6 destino</dt>
            <dd>{selectedBridge.target_ipv6}</dd>
            <dt>Puerto destino</dt>
            <dd>{selectedBridge.target_port}</dd>
            <dt>Estado</dt>
            <dd>{statusLabel(selectedBridge.status)}</dd>
            <dt>Validación TCP</dt>
            <dd>{selectedBridge.last_tcp_validation_result ?? "-"}</dd>
            <dt>Último heartbeat</dt>
            <dd>{selectedBridge.last_heartbeat_result ?? "-"}</dd>
          </dl>
          {selectedBridge.status === "ERROR" && (
            <p className="error">No se pudo conectar al destino IPv6. Verifica dirección, puerto, firewall y que el servicio esté escuchando.</p>
          )}
        </section>
      )}
    </main>
  )
}

export default App
