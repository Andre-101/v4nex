# 02 - Modelo de datos y contrato API

## Resumen ejecutivo

Este escenario define el contrato técnico mínimo del MVP de v4nex: entidades, estados, transiciones, endpoints documentales, formato estándar de errores y reglas de validación.

El alcance es exclusivamente documental. No se implementan endpoints reales, modelos reales, migraciones, autenticación funcional, validación TCP real ni activación dinámica de Caddy en este escenario.

## Supuestos

- La API interna del MVP vive bajo el prefijo `/_v4nex`.
- Los subdominios públicos del MVP usan el dominio `*.v4nex.com`.
- El target inicial de un bridge usa una dirección IPv6 y el puerto `80`.
- El frontend no decide estados finales de bridge.
- El backend es la fuente de verdad para usuarios, bridges, eventos, validaciones, activaciones y estados.
- Los endpoints descritos son contrato documental para escenarios posteriores, no implementación activa en este escenario.

## Fuera de alcance

- Migraciones reales.
- Endpoints reales.
- Auth funcional.
- JWT real.
- Caddy dinámico.
- Validación TCP real.
- TLS real.
- Billing.
- CI/CD.
- `docker-compose.prod.yml`.
- Deploy.

## Modelo de datos mínimo

### User

Representa una cuenta de usuario propietaria de bridges.

Campos:

- `id`: identificador único del usuario.
- `email`: email único del usuario.
- `password_hash`: hash de contraseña. Nunca se expone en respuestas API.
- `created_at`: fecha de creación.
- `updated_at`: fecha de última actualización.

Notas:

- El contrato documenta la entidad necesaria para escenarios posteriores.
- No se implementa auth funcional en este escenario.

### Bridge

Representa la asociación entre un subdominio público y un destino IPv6 HTTP.

Campos:

- `id`: identificador único del bridge.
- `user_id`: propietario del bridge.
- `subdomain`: subdominio asignado sin dominio raíz, por ejemplo `demo`.
- `public_url`: URL pública calculada, por ejemplo `https://demo.v4nex.com`.
- `target_ipv6`: dirección IPv6 destino.
- `target_port`: puerto destino. Para MVP inicial, solo `80`.
- `status`: estado oficial del bridge.
- `last_tcp_validation_at`: fecha de la última validación TCP.
- `last_tcp_validation_result`: resultado de la última validación TCP, por ejemplo `OK` o `FAILED`.
- `last_heartbeat_at`: fecha del último heartbeat.
- `last_heartbeat_result`: resultado del último heartbeat, por ejemplo `OK` o `FAILED`.
- `activated_at`: fecha de activación.
- `disabled_at`: fecha de desactivación.
- `created_at`: fecha de creación.
- `updated_at`: fecha de última actualización.

Notas:

- `public_url` puede ser derivada desde `subdomain`, pero se documenta como campo visible de API.
- Solo el backend puede cambiar `status`.

### BridgeEvent

Representa eventos relevantes del ciclo de vida de un bridge.

Campos:

- `id`: identificador único del evento.
- `bridge_id`: bridge asociado.
- `event_type`: tipo de evento, por ejemplo `BRIDGE_CREATED`, `TCP_VALIDATION_FAILED` o `BRIDGE_ACTIVATED`.
- `message`: mensaje legible para humanos.
- `metadata`: objeto con datos adicionales del evento.
- `created_at`: fecha de creación del evento.

Notas:

- Los eventos alimentan la sección de eventos recientes en UX.
- `metadata` no debe contener secretos.

### BridgeHealthSnapshot

Entidad opcional/futura para guardar muestras históricas de salud del bridge.

No es obligatoria para el MVP inicial. Puede evaluarse en escenarios posteriores si se necesitan métricas históricas, disponibilidad, latencia o tendencias.

Campos candidatos futuros:

- `id`
- `bridge_id`
- `tcp_result`
- `heartbeat_result`
- `checked_at`
- `metadata`

## Estados oficiales de Bridge

### DRAFT

Bridge creado, pero aún no validado.

### VALIDATING

Bridge en proceso de validación técnica.

### READY

Validación TCP exitosa. El bridge está listo para activación, pero aún no está activo.

### ACTIVE

Bridge activo y con ruta pública habilitada.

### ERROR

Bridge con error por validación fallida, activación fallida u otro problema operativo.

### DISABLED

Bridge deshabilitado. No debe exponerse como activo.

### SUSPENDED como futuro

Estado futuro para suspensiones por política, abuso, seguridad, pago u operación. No es obligatorio para el MVP inicial.

## Transiciones válidas

| Desde | Hacia | Motivo |
| --- | --- | --- |
| `DRAFT` | `VALIDATING` | Iniciar validación TCP. |
| `VALIDATING` | `READY` | Validación TCP exitosa. |
| `VALIDATING` | `ERROR` | Validación TCP fallida. |
| `READY` | `ACTIVE` | Activación exitosa. |
| `READY` | `ERROR` | Activación Caddy fallida. |
| `ACTIVE` | `DISABLED` | Deshabilitación solicitada. |
| `ACTIVE` | `ERROR` | Error operativo detectado. |
| `ERROR` | `VALIDATING` | Reintento de validación. |
| `DISABLED` | `VALIDATING` | Revalidación antes de reactivar. |

Reglas:

- Solo el backend cambia el estado de un bridge.
- La activación requiere estado `READY`.
- Una validación TCP fallida deja el bridge en `ERROR`.
- Una activación Caddy fallida deja el bridge en `ERROR`.
- El frontend puede solicitar acciones, pero no debe calcular ni imponer el estado final.

## API contract

Base path:

```text
/_v4nex
```

Todos los endpoints siguientes son documentales para contrato de escenarios posteriores.

### GET /_v4nex/health

Verifica salud básica de la API interna.

Response `200`:

```json
{
  "status": "ok"
}
```

### POST /_v4nex/auth/register

Registra un usuario.

Request:

```json
{
  "email": "user@example.com",
  "password": "string"
}
```

Response `201`:

```json
{
  "id": "uuid",
  "email": "user@example.com"
}
```

### POST /_v4nex/auth/login

Autentica un usuario.

Request:

```json
{
  "email": "user@example.com",
  "password": "string"
}
```

Response `200`:

```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

### GET /_v4nex/bridges

Lista bridges del usuario autenticado.

Response `200`:

```json
[
  {
    "id": "uuid",
    "subdomain": "demo",
    "public_url": "https://demo.v4nex.com",
    "target_ipv6": "2800:...",
    "target_port": 80,
    "status": "ACTIVE",
    "last_tcp_validation_at": "datetime",
    "last_tcp_validation_result": "OK",
    "last_heartbeat_at": "datetime",
    "last_heartbeat_result": "OK"
  }
]
```

### POST /_v4nex/bridges

Crea un bridge en estado inicial `DRAFT`.

Request:

```json
{
  "subdomain": "demo",
  "target_ipv6": "2800:...",
  "target_port": 80
}
```

Response `201`:

```json
{
  "id": "uuid",
  "status": "DRAFT",
  "public_url": "https://demo.v4nex.com"
}
```

### GET /_v4nex/bridges/{bridge_id}

Obtiene el detalle de un bridge.

Response `200`:

```json
{
  "id": "uuid",
  "subdomain": "demo",
  "public_url": "https://demo.v4nex.com",
  "target_ipv6": "2800:...",
  "target_port": 80,
  "status": "ACTIVE",
  "last_tcp_validation_at": "datetime",
  "last_tcp_validation_result": "OK",
  "last_heartbeat_at": "datetime",
  "last_heartbeat_result": "OK",
  "activated_at": "datetime",
  "disabled_at": null,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### POST /_v4nex/bridges/{bridge_id}/validate

Solicita validación TCP del target `[target_ipv6]:80`.

Response `200` success:

```json
{
  "id": "uuid",
  "status": "READY",
  "last_tcp_validation_result": "OK"
}
```

Response `422` o `409` error:

```json
{
  "error": {
    "code": "TCP_VALIDATION_FAILED",
    "message": "TCP validation failed. v4nex could not reach the IPv6 service on port 80."
  }
}
```

### POST /_v4nex/bridges/{bridge_id}/activate

Activa un bridge previamente validado.

Response `200` success:

```json
{
  "id": "uuid",
  "status": "ACTIVE",
  "public_url": "https://demo.v4nex.com"
}
```

### POST /_v4nex/bridges/{bridge_id}/disable

Deshabilita un bridge activo.

Response `200`:

```json
{
  "id": "uuid",
  "status": "DISABLED"
}
```

### GET /_v4nex/bridges/{bridge_id}/events

Lista eventos recientes de un bridge.

Response `200`:

```json
[
  {
    "id": "uuid",
    "bridge_id": "uuid",
    "event_type": "BRIDGE_ACTIVATED",
    "message": "Bridge activated successfully.",
    "metadata": {},
    "created_at": "datetime"
  }
]
```

## Error format estándar

Todas las respuestas de error deben seguir este formato:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
```

Códigos:

- `INVALID_EMAIL`
- `EMAIL_ALREADY_EXISTS`
- `INVALID_CREDENTIALS`
- `INVALID_SUBDOMAIN`
- `RESERVED_SUBDOMAIN`
- `SUBDOMAIN_ALREADY_EXISTS`
- `INVALID_IPV6`
- `INVALID_PORT`
- `BRIDGE_NOT_FOUND`
- `INVALID_STATE_TRANSITION`
- `TCP_VALIDATION_FAILED`
- `CADDY_ACTIVATION_FAILED`
- `UNAUTHORIZED`
- `INTERNAL_ERROR`

## Reglas de validación

### Subdomain

- Debe tener entre 3 y 40 caracteres.
- Solo puede usar letras minúsculas, números y guion.
- No puede iniciar con guion.
- No puede terminar con guion.
- No puede estar reservado.
- No puede estar duplicado.

Reservados:

- `www`
- `api`
- `admin`
- `panel`
- `login`
- `dashboard`
- `status`
- `mail`
- `smtp`
- `ftp`
- `ssh`
- `root`
- `support`
- `billing`
- `docs`
- `dev`
- `test`
- `_v4nex`

`_v4nex` queda reservado como nombre técnico adicional por la ruta interna de plataforma `/_v4nex/*`.

### IPv6

- No puede estar vacía.
- Debe tener formato IPv6 válido.
- Los rangos de documentación no deberían aceptarse en producción.

### Port

- Para el MVP inicial solo se permite `80`.

## Criterios de aceptación del Escenario 2

- Existe `docs/02-data-model-and-api-contract.md`.
- No hay cambios de código.
- El documento define entidades mínimas.
- El documento define estados y transiciones.
- El documento define endpoints bajo `/_v4nex`.
- El documento define formato estándar de error.
- El documento define validaciones mínimas.
- Se mantiene fuera de alcance implementación funcional.
