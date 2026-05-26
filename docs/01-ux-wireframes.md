# 01 - UX y wireframes

## Objetivo

Definir la experiencia de usuario del MVP de v4nex para el flujo de descubrimiento, acceso y creación de un bridge IPv6 -> subdominio público.

Este escenario documenta comportamiento esperado, estructura de pantallas, mensajes y estados visuales. No define UI final ni implementación funcional.

## Resumen ejecutivo del flujo MVP

El MVP permite que una persona entienda la propuesta de v4nex, cree una cuenta conceptual, acceda a un dashboard y configure un bridge básico asociando un subdominio público con una dirección IPv6 y el puerto HTTP `80`.

Flujo principal:

1. La persona llega a la landing y entiende que v4nex expone un servicio IPv6 propio mediante una URL pública.
2. Desde la landing entra a registro o login.
3. En el dashboard ve sus bridges y el estado general de cada uno.
4. Inicia el wizard de creación de bridge.
5. Escribe un subdominio y ve el preview `https://subdominio.v4nex.com`.
6. Ingresa una IPv6 y confirma que el puerto objetivo será `80`.
7. Ejecuta validación.
8. Si la validación pasa, el bridge queda en `Ready`.
9. Activa el bridge.
10. El bridge queda en `Active` y se muestra su detalle con URL pública, destino IPv6 y estado operativo.

## Principios UX del MVP

- Claridad antes que densidad: cada pantalla debe explicar una decisión principal, no todas las capacidades futuras.
- Confianza operativa: los estados deben comunicar qué está configurado, qué falta y qué requiere acción.
- Progresión guiada: la creación de bridge debe sentirse como un wizard corto, con preview visible y validaciones explícitas.
- Errores accionables: cada error debe indicar qué falló y qué puede corregir la persona.
- Baja promesa comercial: evitar claims de producción, billing, métricas avanzadas o planes mientras no existan.
- Separación de intención y activación: validar un bridge no debe implicar activarlo automáticamente.
- Diseño preparado para futuro: incluir `Suspended` como estado futuro sin habilitar comportamiento funcional en el MVP.

## Mapa de pantallas

### Landing

Pantalla pública para explicar el valor del MVP y dirigir a registro/login.

Objetivo principal:

- Comunicar que v4nex permite publicar un endpoint HTTP propio mediante `https://subdominio.v4nex.com`.

Acciones:

- Ir a registro.
- Ir a login.

### Registro

Pantalla conceptual para alta de usuario.

Objetivo principal:

- Presentar el punto de entrada para crear cuenta sin implementar autenticación funcional en este escenario.

Acciones:

- Completar datos de registro.
- Continuar hacia dashboard en wireframe conceptual.
- Ir a login.

### Login

Pantalla conceptual para acceso de usuario existente.

Objetivo principal:

- Presentar el punto de entrada para usuarios existentes sin implementar login funcional en este escenario.

Acciones:

- Completar credenciales.
- Continuar hacia dashboard en wireframe conceptual.
- Ir a registro.

### Dashboard

Pantalla principal posterior al acceso.

Objetivo principal:

- Mostrar lista de bridges, estados y acceso rápido a crear uno nuevo.

Acciones:

- Crear bridge.
- Abrir detalle de bridge.
- Ver estado general de cada bridge.

### Crear bridge wizard

Flujo guiado de creación.

Objetivo principal:

- Capturar subdominio e IPv6, validar conectividad TCP al puerto `80`, dejar el bridge en `Ready` y permitir activarlo.

Acciones:

- Escribir subdominio.
- Ver preview de URL pública.
- Ingresar IPv6.
- Validar.
- Activar.
- Cancelar y volver al dashboard.

### Detalle de bridge

Pantalla de inspección de un bridge existente.

Objetivo principal:

- Mostrar configuración, URL pública, destino IPv6, puerto, estado y acciones disponibles según estado.

Acciones:

- Copiar URL pública.
- Ver estado.
- Activar si está `Ready`.
- Deshabilitar si está `Active`.
- Volver al dashboard.

## Wireframes textuales por pantalla

### Landing

```text
+------------------------------------------------------------+
| v4nex                                      Login | Registro |
+------------------------------------------------------------+
| Publica tu servicio IPv6 con una URL simple                 |
|                                                            |
| https://tu-subdominio.v4nex.com -> [IPv6]:80               |
|                                                            |
| [Crear bridge] [Entrar]                                    |
|                                                            |
| Flujo MVP: subdominio, IPv6, validación y activación.       |
+------------------------------------------------------------+
```

Notas:

- El mensaje debe evitar prometer producción, SLA, billing o métricas.
- La URL ejemplo debe ser visible en el primer viewport.

### Registro

```text
+------------------------------------------------------------+
| v4nex                                                      |
+------------------------------------------------------------+
| Crear cuenta                                               |
|                                                            |
| Nombre                                                     |
| [......................................................]   |
|                                                            |
| Email                                                      |
| [......................................................]   |
|                                                            |
| Contraseña                                                 |
| [......................................................]   |
|                                                            |
| [Crear cuenta]                                             |
|                                                            |
| ¿Ya tienes cuenta? Entrar                                  |
+------------------------------------------------------------+
```

Notas:

- Wireframe conceptual. No implica login funcional ni persistencia real en este escenario.
- Mensajes de validación de formulario quedan como referencia visual, no implementación.

### Login

```text
+------------------------------------------------------------+
| v4nex                                                      |
+------------------------------------------------------------+
| Entrar                                                     |
|                                                            |
| Email                                                      |
| [......................................................]   |
|                                                            |
| Contraseña                                                 |
| [......................................................]   |
|                                                            |
| [Entrar]                                                   |
|                                                            |
| ¿No tienes cuenta? Crear cuenta                            |
+------------------------------------------------------------+
```

Notas:

- Wireframe conceptual. No agrega autenticación funcional.
- No incluir recuperación de contraseña en el MVP.

### Dashboard

```text
+------------------------------------------------------------+
| v4nex Dashboard                              [Crear bridge] |
+------------------------------------------------------------+
| Bridges                                                    |
|                                                            |
| +----------------------+----------------------+----------+ |
| | Subdominio           | Destino              | Estado   | |
| +----------------------+----------------------+----------+ |
| | demo.v4nex.com       | [IPv6]:80            | Active   | |
| | staging.v4nex.com    | [IPv6]:80            | Ready    | |
| | test.v4nex.com       | [IPv6]:80            | Error    | |
| +----------------------+----------------------+----------+ |
|                                                            |
| Estado vacío:                                              |
| Aún no tienes bridges. Crea el primero para validar IPv6.   |
+------------------------------------------------------------+
```

Notas:

- Cada fila debe abrir el detalle del bridge.
- El estado visual debe ser legible sin depender solo del color.

### Crear bridge wizard

```text
+------------------------------------------------------------+
| Crear bridge                                      Paso 1/3  |
+------------------------------------------------------------+
| Subdominio                                                 |
| [ mi-servicio                                      ]        |
|                                                            |
| Preview                                                    |
| https://mi-servicio.v4nex.com                              |
|                                                            |
| [Continuar]                                                |
+------------------------------------------------------------+

+------------------------------------------------------------+
| Crear bridge                                      Paso 2/3  |
+------------------------------------------------------------+
| Destino IPv6                                               |
| [ 2800:...                                        ]        |
|                                                            |
| Puerto                                                     |
| [80] fijo para MVP                                         |
|                                                            |
| [Validar]                                                  |
+------------------------------------------------------------+

+------------------------------------------------------------+
| Crear bridge                                      Paso 3/3  |
+------------------------------------------------------------+
| Validación                                                 |
|                                                            |
| Estado: Ready                                              |
| URL: https://mi-servicio.v4nex.com                         |
| Destino: [IPv6]:80                                         |
|                                                            |
| [Activar bridge] [Volver al dashboard]                     |
+------------------------------------------------------------+
```

Notas:

- El puerto `80` se muestra como valor fijo del MVP.
- `Validating` debe aparecer mientras se ejecuta la validación.
- `Ready` aparece solo después de validación exitosa.
- `Active` aparece solo después de activar.

### Detalle de bridge

```text
+------------------------------------------------------------+
| Bridge: mi-servicio                              Estado     |
+------------------------------------------------------------+
| URL pública                                                |
| https://mi-servicio.v4nex.com                    [Copiar]  |
|                                                            |
| Destino                                                    |
| IPv6: 2800:...                                             |
| Puerto: 80                                                 |
|                                                            |
| Estado actual                                              |
| Active                                                     |
|                                                            |
| Eventos recientes                                          |
| - Validación TCP exitosa                                   |
| - Activación Caddy exitosa                                 |
|                                                            |
| [Deshabilitar] [Volver]                                    |
+------------------------------------------------------------+
```

Notas:

- Para `Ready`, la acción principal es `Activar bridge`.
- Para `Error`, mostrar mensaje específico y permitir reintentar validación cuando aplique.
- Para `Disabled`, mostrar opción conceptual de reactivar si el MVP lo permite en un escenario posterior.

## Estados visuales

### Draft

- Uso: bridge iniciado pero incompleto.
- Color sugerido: neutro.
- Texto: `Draft`.
- Acción principal: completar datos.

### Validating

- Uso: validación en curso.
- Color sugerido: informativo.
- Texto: `Validating`.
- Acción principal: esperar resultado.
- La UI debe bloquear doble envío de validación.

### Ready

- Uso: validación exitosa, pendiente de activación.
- Color sugerido: positivo moderado.
- Texto: `Ready`.
- Acción principal: activar bridge.

### Active

- Uso: bridge activo y enrutable.
- Color sugerido: positivo fuerte.
- Texto: `Active`.
- Acción principal: ver detalle o deshabilitar.

### Error

- Uso: validación o activación fallida.
- Color sugerido: crítico.
- Texto: `Error`.
- Acción principal: corregir datos o reintentar.

### Disabled

- Uso: bridge desactivado por decisión del usuario o administración manual.
- Color sugerido: neutro apagado.
- Texto: `Disabled`.
- Acción principal: ver detalle. Reactivación queda sujeta a escenario futuro.

### Suspended como futuro

- Uso futuro: bridge suspendido por política, abuso, pago, seguridad u operación.
- Color sugerido: advertencia.
- Texto: `Suspended`.
- Acción principal futura: contactar soporte o resolver condición.
- No debe implementarse comportamiento funcional de suspensión en el MVP.

## Mensajes de error

### Subdominio inválido

Mensaje:

> El subdominio solo puede usar letras minúsculas, números y guiones. Debe iniciar y terminar con letra o número.

Guía visual:

- Marcar el campo de subdominio.
- Mantener visible el preview si puede generarse parcialmente, o reemplazarlo por `https://subdominio.v4nex.com`.

### Subdominio reservado

Mensaje:

> Este subdominio está reservado. Elige otro nombre.

Ejemplos reservados:

- `www`
- `api`
- `admin`
- `root`
- `support`
- `status`
- `_v4nex`

### Subdominio duplicado

Mensaje:

> Este subdominio ya está en uso. Prueba con otro.

Guía visual:

- Mantener a la persona en el paso de subdominio.
- No permitir avanzar hasta elegir uno disponible.

### IPv6 inválida

Mensaje:

> La dirección IPv6 no tiene un formato válido.

Guía visual:

- Marcar el campo IPv6.
- No ejecutar validación TCP hasta corregir el formato.

### TCP validation failed

Mensaje:

> No se pudo conectar por TCP al destino IPv6 en el puerto 80. Verifica que el servicio esté activo y accesible.

Guía visual:

- Estado del bridge: `Error`.
- Acción recomendada: revisar IPv6, firewall y servicio HTTP.
- Permitir reintentar validación.

### Caddy activation failed

Mensaje:

> La validación fue exitosa, pero no se pudo activar la ruta pública. Intenta de nuevo o revisa la configuración del proxy.

Guía visual:

- Estado del bridge: `Error`.
- Mantener visibles URL pública y destino configurado.
- Permitir reintentar activación si el sistema lo soporta en el escenario funcional.

## Flujo de creación de bridge

1. Escribir subdominio.
2. Mostrar preview inmediato: `https://subdominio.v4nex.com`.
3. Validar formato del subdominio.
4. Validar que el subdominio no esté reservado.
5. Validar que el subdominio no esté duplicado.
6. Ingresar dirección IPv6.
7. Mostrar puerto `80` como destino fijo del MVP.
8. Validar formato IPv6.
9. Ejecutar validación TCP hacia `[IPv6]:80`.
10. Mientras valida, mostrar estado `Validating`.
11. Si la validación falla, mostrar `Error` con mensaje específico.
12. Si la validación pasa, mostrar estado `Ready`.
13. Activar bridge.
14. Si la activación falla, mostrar `Caddy activation failed`.
15. Si la activación pasa, mostrar estado `Active`.
16. Redirigir o permitir navegar al detalle del bridge.

## Fuera de alcance

- Billing.
- Métricas avanzadas.
- Ancho de banda.
- Planes comerciales.
- UI final.
- Implementación funcional.
- Login funcional.
- Bridges funcionales.
- Integraciones de producción.
- CI/CD.
- `docker-compose.prod.yml`.
- Deploy.

## Criterios de aceptación del Escenario 1

- Existe `docs/01-ux-wireframes.md`.
- El documento describe el flujo MVP desde landing hasta bridge activo.
- El documento incluye principios UX del MVP.
- El documento incluye mapa de pantallas para landing, registro, login, dashboard, wizard de creación y detalle de bridge.
- El documento incluye wireframes textuales para cada pantalla.
- El documento define estados visuales: `Draft`, `Validating`, `Ready`, `Active`, `Error`, `Disabled` y `Suspended` como futuro.
- El documento define mensajes para subdominio inválido, subdominio reservado, subdominio duplicado, IPv6 inválida, `TCP validation failed` y `Caddy activation failed`.
- El documento describe el flujo de creación de bridge con subdominio, preview, IPv6, puerto `80`, validación, `Ready`, activación y `Active`.
- El documento declara explícitamente lo que queda fuera de alcance.
- No se implementa UI final.
- No se modifica lógica de backend.
- No se agrega login funcional.
- No se agregan bridges funcionales.
- No se agrega CI/CD.
- No se agrega `docker-compose.prod.yml`.
- No se realiza deploy.
