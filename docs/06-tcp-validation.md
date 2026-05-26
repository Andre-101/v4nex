# 06 - Validación TCP real controlada

## Resumen ejecutivo

Este escenario agrega validación TCP real para bridges existentes, sin activar Caddy, sin publicar tráfico y sin crear endpoints de activación o desactivación.

La validación usa `socket` de la librería estándar, intenta abrir una conexión TCP al `target_ipv6` y `target_port` del bridge, registra eventos operativos y actualiza el estado del bridge según el resultado.

## Qué se implementó

- Servicio interno `validate_tcp_connectivity`.
- Resultado estructurado `TcpValidationResult`.
- Medición aproximada de latencia en milisegundos.
- Timeout estricto configurable.
- Cierre garantizado del socket.
- Soporte IPv6 mediante `socket.AF_INET6`.
- Endpoint autenticado:
  - `POST /_v4nex/bridges/{bridge_id}/validate`
- Persistencia de:
  - `status`
  - `last_tcp_validation_at`
  - `last_tcp_validation_result`
  - eventos de validación

## Fuera de alcance

- Caddy dinámico.
- Reload de Caddy.
- Activación real.
- Endpoint `activate`.
- Endpoint `disable`.
- TLS real.
- Frontend funcional.
- CI/CD.
- Deploy.
- Heartbeat real.
- Billing.
- Rate limiting real.
- Métricas avanzadas.

## Estados y transiciones

El endpoint `validate` solo puede iniciar desde:

- `DRAFT`
- `ERROR`
- `DISABLED`

Transiciones usadas:

- `DRAFT -> VALIDATING`
- `ERROR -> VALIDATING`
- `DISABLED -> VALIDATING`
- `VALIDATING -> READY`
- `VALIDATING -> ERROR`

Reglas:

- Si el bridge no existe o pertenece a otro usuario, responde `BRIDGE_NOT_FOUND`.
- Si el estado no permite validación, responde `INVALID_STATE_TRANSITION`.
- Si la conexión TCP pasa, el bridge queda `READY`.
- Si la conexión TCP falla, el bridge queda `ERROR`.
- No se modifica `public_url`.
- No se activa Caddy.

## Eventos generados

La validación genera eventos en `bridge_events`:

- `TCP_VALIDATION_STARTED`
- `TCP_VALIDATION_PASSED`
- `TCP_VALIDATION_FAILED`

Metadata permitida:

- `target_ipv6`
- `target_port`
- `error_code`
- `latency_ms`

No se guardan secretos en metadata.

## Códigos internos TCP

- `TCP_OK`
- `TCP_TIMEOUT`
- `TCP_CONNECTION_REFUSED`
- `TCP_UNREACHABLE`
- `TCP_DNS_ERROR`
- `TCP_UNKNOWN_ERROR`

## Cómo correr tests

Desde `apps/backend`:

```bash
python -m pytest -p no:cacheprovider
```

Los tests del endpoint usan monkeypatch del servicio TCP, por lo que no dependen de red externa.

## Smoke manual opcional

Si el entorno local soporta IPv6 loopback y se quiere probar manualmente:

1. Levantar un servicio TCP local escuchando en IPv6.
2. Crear un bridge autenticado con `target_ipv6` apuntando a esa dirección y `target_port=80`.
3. Ejecutar:

```bash
curl -X POST http://localhost:8000/_v4nex/bridges/BRIDGE_ID/validate \
  -H "Authorization: Bearer TOKEN"
```

Resultados esperados:

- Si el puerto acepta conexión TCP: `status=READY`.
- Si no acepta conexión TCP: error estándar `TCP_VALIDATION_FAILED` y bridge en `ERROR`.

Este smoke no es requerido para la suite automática.

## Riesgos y pendientes

- Definir límites de concurrencia para validaciones reales.
- Agregar observabilidad mínima de duración y fallos.
- Decidir si la validación debe ejecutarse síncrona o en background en escenarios posteriores.
- Implementar activación Caddy real recién cuando el flujo `READY -> ACTIVE` sea parte del alcance.
- Mantener `activate` y `disable` fuera hasta que existan garantías operativas.
