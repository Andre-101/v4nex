import { FormEvent, useEffect, useState } from "react"

type Bridge = {
  id: string
  subdomain: string
  public_url: string
  target_ipv6: string
  target_port: number
  status: string
  last_tcp_validation_result?: string | null
}

type ApiError = {
  error?: {
    code?: string
    message?: string
    details?: Record<string, unknown>
  }
}

const endpoints = {
  register: "/_v4nex/auth/register",
  login: "/_v4nex/auth/login",
  bridges: "/_v4nex/bridges",
}

const allowedPorts = [80, 8080]

function isPreviewAllowed() {
  if (typeof window === "undefined") return false
  return ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname)
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
      id: "preview-bridge",
      subdomain: "preview",
      public_url: "https://preview.v4nex.com",
      target_ipv6: "2606:4700:4700::1111",
      target_port: 80,
      status: "DRAFT",
      last_tcp_validation_result: null,
    },
  ]
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

function allowedPortsText(details?: Record<string, unknown>) {
  const ports = details?.allowed_ports
  if (Array.isArray(ports) && ports.length > 0) {
    return ` Puertos permitidos: ${ports.join(", ")}.`
  }
  return ""
}

async function parseResponse<T>(response: Response): Promise<T> {
  const body = (await response.json().catch(() => ({}))) as ApiError
  if (!response.ok) {
    const message = body.error?.message || body.error?.code || "Solicitud no completada."
    throw new Error(`${message}${allowedPortsText(body.error?.details)}`)
  }
  return body as T
}

function App() {
  const [token, setToken] = useState(getInitialToken)
  const [email, setEmail] = useState(getInitialEmail)
  const [isPreview, setIsPreview] = useState(isPreviewSession)
  const [authMode, setAuthMode] = useState<"login" | "register">("login")
  const [authEmail, setAuthEmail] = useState("")
  const [password, setPassword] = useState("")
  const [authMessage, setAuthMessage] = useState("")
  const [authError, setAuthError] = useState("")
  const [bridges, setBridges] = useState<Bridge[]>(isPreviewSession() ? getPreviewBridges() : [])
  const [bridgesError, setBridgesError] = useState("")
  const [loadingBridges, setLoadingBridges] = useState(false)
  const [subdomain, setSubdomain] = useState("")
  const [targetIpv6, setTargetIpv6] = useState("")
  const [targetPort, setTargetPort] = useState(80)
  const [createMessage, setCreateMessage] = useState("")
  const [createError, setCreateError] = useState("")

  const isAuthenticated = Boolean(token)

  async function loadBridges() {
    if (!token || isPreview) return

    setLoadingBridges(true)
    setBridgesError("")
    try {
      const data = await parseResponse<Bridge[]>(
        await fetch(endpoints.bridges, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      )
      setBridges(data)
    } catch (error) {
      setBridgesError(isNetworkError(error) ? networkErrorMessage() : "No pudimos cargar los bridges.")
    } finally {
      setLoadingBridges(false)
    }
  }

  useEffect(() => {
    void loadBridges()
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
      )
      sessionStorage.setItem("v4nex_access_token", data.access_token)
      sessionStorage.setItem("v4nex_user_email", authEmail)
      sessionStorage.removeItem("v4nex_preview_session")
      setToken(data.access_token)
      setEmail(authEmail)
      setIsPreview(false)
      setPassword("")
    } catch (error) {
      if (isNetworkError(error)) {
        setAuthError(networkErrorMessage())
        return
      }
      setAuthError(
        authMode === "login"
          ? "No pudimos iniciar sesion. Revisa tus credenciales."
          : "No pudimos crear la cuenta. Verifica el correo y la contrasena.",
      )
    }
  }

  function startPreview() {
    if (!isPreviewAllowed()) return
    sessionStorage.setItem("v4nex_preview_session", "true")
    sessionStorage.removeItem("v4nex_access_token")
    sessionStorage.removeItem("v4nex_user_email")
    setToken("local-preview-token")
    setEmail("preview@v4nex.local")
    setIsPreview(true)
    setBridges(getPreviewBridges())
    setAuthError("")
    setAuthMessage("")
  }

  function logout() {
    sessionStorage.removeItem("v4nex_access_token")
    sessionStorage.removeItem("v4nex_user_email")
    sessionStorage.removeItem("v4nex_preview_session")
    setToken("")
    setEmail("")
    setIsPreview(false)
    setBridges([])
    setBridgesError("")
    setCreateMessage("")
    setCreateError("")
  }

  async function submitBridge(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setCreateError("")
    setCreateMessage("")

    if (isPreview) {
      setBridges((current) => [
        {
          id: `preview-${Date.now()}`,
          subdomain,
          public_url: `https://${subdomain}.v4nex.com`,
          target_ipv6: targetIpv6,
          target_port: targetPort,
          status: "DRAFT",
          last_tcp_validation_result: null,
        },
        ...current,
      ])
      setSubdomain("")
      setTargetIpv6("")
      setTargetPort(80)
      setCreateMessage("Bridge creado localmente en estado DRAFT.")
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
          body: JSON.stringify({
            subdomain,
            target_ipv6: targetIpv6,
            target_port: targetPort,
          }),
        }),
      )
      setSubdomain("")
      setTargetIpv6("")
      setTargetPort(80)
      setCreateMessage("Bridge creado en estado DRAFT.")
      await loadBridges()
    } catch (error) {
      if (isNetworkError(error)) {
        setCreateError(networkErrorMessage())
        return
      }
      setCreateError(
        error instanceof Error
          ? `No pudimos crear el bridge.${error.message.includes("Puertos permitidos") ? error.message : ""}`
          : "No pudimos crear el bridge.",
      )
    }
  }

  if (!isAuthenticated) {
    return (
      <main className="app">
        <section className="panel">
          <h1>v4nex</h1>
          <p className="muted">Edge Connectivity. Limitless Access.</p>
          <p>
            Publica servicios IPv6 detras de una entrada IPv4 con dominios, TLS y reverse proxy L7.
          </p>
        </section>

        <section className="panel">
          <div className="tabs">
            <button className={authMode === "login" ? "active" : ""} type="button" onClick={() => setAuthMode("login")}>
              Entrar
            </button>
            <button
              className={authMode === "register" ? "active" : ""}
              type="button"
              onClick={() => setAuthMode("register")}
            >
              Crear cuenta
            </button>
          </div>

          <form onSubmit={submitAuth}>
            <label>
              Email
              <input type="email" value={authEmail} onChange={(event) => setAuthEmail(event.target.value)} required />
            </label>
            <label>
              Contrasena
              <input
                type="password"
                value={password}
                minLength={8}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
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
          Cerrar sesion
        </button>
      </header>

      <section className="grid">
        <div className="panel">
          <h2>Resumen</h2>
          <p>Total bridges: {bridges.length}</p>
          <p>Ready: {bridges.filter((bridge) => bridge.status === "READY").length}</p>
          <p>Active: {bridges.filter((bridge) => bridge.status === "ACTIVE").length}</p>
        </div>

        <div className="panel">
          <h2>Nuevo bridge</h2>
          <form onSubmit={submitBridge}>
            <label>
              Subdominio
              <input value={subdomain} onChange={(event) => setSubdomain(event.target.value)} required />
            </label>
            <label>
              IPv6 destino
              <input value={targetIpv6} onChange={(event) => setTargetIpv6(event.target.value)} required />
            </label>
            <label>
              Puerto destino
              <select value={targetPort} onChange={(event) => setTargetPort(Number(event.target.value))}>
                {allowedPorts.map((port) => (
                  <option key={port} value={port}>
                    {port === 80 ? "80 - HTTP" : "8080 - HTTP alternativo"}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit">Crear bridge</button>
          </form>
          {createMessage && <p className="success">{createMessage}</p>}
          {createError && <p className="error">{createError}</p>}
        </div>
      </section>

      <section className="panel">
        <div className="section-header">
          <h2>Bridges</h2>
          <button className="secondary" type="button" onClick={() => void loadBridges()} disabled={loadingBridges || isPreview}>
            {loadingBridges ? "Actualizando..." : "Actualizar"}
          </button>
        </div>

        {bridgesError && <p className="error">{bridgesError}</p>}

        {bridges.length === 0 ? (
          <p className="muted">Aun no tienes bridges configurados.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Subdominio</th>
                  <th>URL publica</th>
                  <th>IPv6 destino</th>
                  <th>Puerto</th>
                  <th>Estado</th>
                  <th>Validacion TCP</th>
                </tr>
              </thead>
              <tbody>
                {bridges.map((bridge) => (
                  <tr key={bridge.id}>
                    <td>{bridge.subdomain}</td>
                    <td>{bridge.public_url}</td>
                    <td>{bridge.target_ipv6}</td>
                    <td>{bridge.target_port}</td>
                    <td>{bridge.status}</td>
                    <td>{bridge.last_tcp_validation_result ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  )
}

export default App
