# Datacil Client for Odoo 18

Consulta cédulas y RUC ecuatorianos en [Datacil](https://datacil.com) desde Odoo y
autocompleta los datos del contacto, con pantallas de carga y de error claras.

## Módulos

| Módulo | Se instala cuando | Qué aporta |
|---|---|---|
| `datacil_client_odoo` | siempre (núcleo) | Cliente HTTP (`datacil.api`), configuración por compañía, botón **Validar** en contactos **y en el formulario de cliente del Punto de Venta**, pestaña *Datacil* con datos del SRI, panel de créditos en Ajustes, dashboard de créditos/historial/costos |
| `datacil_client_odoo_crm` | `crm` | Campo *Cédula / RUC* en iniciativas/oportunidades con consulta; enlaza el cliente existente y traslada la identificación al crear el contacto |
| `datacil_client_odoo_sale` | `sale` | Alerta en pedidos si el RUC del cliente está suspendido/cancelado o es empresa fantasma; botón *Verificar en Datacil* |
| `datacil_client_odoo_purchase` | `purchase` | Igual que ventas, para proveedores |
| `datacil_client_odoo_repair` | `repair` | Igual, para órdenes de reparación (taller) |
| `datacil_client_odoo_fleet` | `fleet` | Consulta por placa: chasis, color, año, marca/modelo (si existen en el catálogo), propietario, valores pendientes y citaciones |
| `datacil_client_odoo_hr` | `hr` | Pestaña *Datacil* en empleados: identidad, licencia de conducir, antecedentes judiciales y ANT, con notas en el chatter |
| `datacil_client_odoo_website` | `website` | Opción por sitio web para autocompletar el formulario de dirección (modo *solo nombre* gratis o *datos completos*) |
| `datacil_client_odoo_partner_autocomplete` | `partner_autocomplete` | El autocompletado nativo de contactos (IAP) se sirve desde Datacil para Ecuador |

Todos los módulos complementarios son `auto_install`: se instalan solos cuando la app
correspondiente está presente y no generan errores si no lo está.

## Actualización desde la versión 1.x

Al actualizar `datacil_client_odoo` en una base existente, la migración instala
automáticamente los módulos complementarios cuya app ya esté instalada (el botón
*Actualizar* de Odoo por sí solo no instala módulos `auto_install`) y retira el
antiguo `datacil_client_odoo_pos`, cuyo contenido ahora forma parte del núcleo.
Si falta alguno, basta con instalarlo desde Apps o con `odoo -d <db> -i <módulo>`.
Tras actualizar, recarga la sesión del POS para que tome el nuevo bundle de assets.

## Configuración

Ajustes › Datacil: URL, clave API, tiempo máximo de respuesta y si se permite cargar
datos de clientes ya registrados. El bloque **Créditos** muestra el saldo (cacheado,
sin llamadas HTTP al abrir Ajustes) con el botón *Actualizar y probar conexión*.

## Qué campos nativos se rellenan

| Modelo | Campos nativos que completa Datacil |
|---|---|
| `res.partner` | `name`, `vat`, `street` (vía y número), `street2` (referencias), `city`, `zip`, `state_id`, `country_id`, `email`, `phone`, `company_type`, `industry_id` (si la actividad del SRI coincide con un sector existente), `l10n_latam_identification_type_id` |
| `hr.employee` | `identification_id`, `legal_name` (mientras sea el nombre por defecto), `birthday`, `sex`, `country_id` (nacionalidad), `private_street`, `private_street2`, `private_city`, `private_zip`, `private_state_id`, `private_country_id`, `private_email`, `private_phone` — **solo los que estén vacíos** |
| `fleet.vehicle` | `license_plate`, `model_id` (crea marca/modelo en el catálogo si no existen), `vin_sn`, `color`, `model_year`, `fuel_type`, `transmission`, `seats`, `doors`, `power`, `car_value` (avalúo), `acquisition_date` (matrícula), `driver_id` (propietario si ya es contacto) |
| `crm.lead` | `partner_name` o `contact_name`, `street`, `street2`, `zip`, `city`, `state_id`, `country_id`, `email_from`, `phone`, `industry_id`, `partner_id` |
| Sitio web | `name`, `company_name`, `street`, `street2`, `city`, `zip`, `state_id`, `country_id`, `phone`, `email` (solo los vacíos del formulario) |

Lo que la API entrega y Odoo no tiene campo nativo (estado del RUC, régimen, actividad,
licencia de conducir, citaciones ANT, antecedentes judiciales) queda en los campos
`datacil_*` y en la pestaña *Datacil*, con el JSON completo y una nota en el chatter.

La dirección del SRI llega etiquetada (`Calle: … Número: … Referencia: …`): se parte en
`street` (vía, número e intersección) y `street2` (referencias), en vez de meter todo
el texto en una sola línea.

## Cómo funciona una consulta

1. El botón es un *view widget* (`<widget name="datacil_lookup" field="vat" method="..."/>`),
   no un campo ni un `onchange`: no hay llamadas al servidor hasta que se pulsa.
2. Al pulsar se bloquea la interfaz con un mensaje explícito (y otro distinto si tarda
   más de 8 s), se llama al método Python indicado y se muestra:
   * **Diálogo de resultado** con los datos encontrados, créditos restantes y botón
     *Aplicar datos* (los valores se aplican con `record.update`, sin guardar).
   * **Diálogo de error** específico: no configurado (con acceso a Ajustes), sin créditos
     (con acceso al panel), servicio caído (reintentar), clave rechazada, identificación
     inválida / no encontrada, contacto ya registrado (abrirlo). Cuando falta la
     configuración no se ofrece navegar a Ajustes (el formulario puede estar sin guardar);
     el diálogo indica dónde configurarlo.
3. Los métodos Python devuelven siempre el dict de `datacil.api._result()` y nunca
   lanzan excepciones por problemas de red o de la API.

## Rendimiento

* Sin `onchange` ni campos calculados costosos en el formulario de contactos.
* Saldo de créditos cacheado en `datacil.config` (5 min) y actualizado tras cada
  consulta con costo; costos de endpoints cacheados una hora por worker.
* Dashboard en una sola llamada RPC (`/datacil/dashboard`).
* Assets sólo en los bundles necesarios (backend y POS en el núcleo; frontend sólo en el módulo de sitio web).
* Alertas en pedidos con campos `related` (sin cálculos adicionales).

## Tests

```bash
odoo -d <db> -i datacil_client_odoo --test-enable --test-tags datacil --stop-after-init
```

Los tests simulan la API con `unittest.mock` (nunca consumen créditos) y cubren el
cliente HTTP, el mapeo de errores, el autocompletado de contactos, la configuración y
cada módulo complementario.
