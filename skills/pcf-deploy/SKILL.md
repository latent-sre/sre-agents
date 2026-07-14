---
name: pcf-deploy
description: >-
  Plan human-approved VMware TAS/PCF application deploys, blue-green cutovers, scaling, and
  rollback verification. Triggers: 'deploy this app to PCF', 'design a blue-green deploy',
  'scale this PCF app'. Ownership map only—not a load: canonical `release-gate` decides
  readiness and canonical `incident-command` owns rollback decisions.
compatibility: Requires the cf CLI v8 and authorized access to the target PCF foundation/space
# Deploys are human-initiated: invoke explicitly as Copilot `/pcf-deploy` or Claude `/sre-agents:pcf-deploy`; never auto-load.
disable-model-invocation: true
---

# PCF / TAS deploy planning (cf CLI v8)

This skill produces a deployment plan and evidence checklist. **Agents never execute deployment.**
A human release owner executes only after approving the exact target, commands, blast radius,
verification, and rollback.

Before executing a prod deploy, require an evidence packet showing the release and production-change
gates were completed by their owner; if it is absent, stop and report the missing approval. This skill
does not load or run either gate. Show the manifest diff and rollback path before a human acts.

> ### ⚠️ What a rollback does NOT reverse
>
> A route swap or `cf rollback` reverses **code + start command + revision-scoped environment
> variables**. It does not reverse data/schema changes, service bindings, routes, scale, app features,
> or actions consumers already took from the new version's output.
>
> Design database changes with expand → backfill → dual-write → contract, and do not contract
> until the old code is gone. Ownership map only—not a load: canonical `database-reliability` owns
> operational migration safety. "We can roll back" remains `[unverified]` until rehearsed evidence
> proves it for the exact artifact and target.

**Starter:** copy [manifest.yml](./assets/manifest.yml)—a health-checked, multi-instance,
service-bound manifest with stable-live-name notes.

## Manifest (declarative, in version control)

```yaml
applications:
  - name: checkout
    instances: 3
    memory: 1G
    buildpacks: [java_buildpack_offline]
    routes:
      - route: checkout.apps.example.com
    env:
      SPRING_PROFILES_ACTIVE: prod
```

Keep secrets out of manifests; use approved service bindings or the foundation credential service.
Manifest and binding behavior on the target foundation remains `[unverified]` until captured there.

## Blue-green (classic) — preferred for prod

The live app keeps the stable name (`checkout`); green is always the disposable one. Names rotate
after the soak, so the playbook is identical on every run—there is no "blue" app, ever.

```bash
cf push checkout-green -f manifest.yml --no-route     # candidate beside live; never touches it
cf map-route checkout-green apps.example.com --hostname checkout-test
# smoke-test green on the test route
cf map-route checkout-green apps.example.com --hostname checkout    # green joins prod
cf unmap-route checkout apps.example.com --hostname checkout        # all prod traffic on green
# soak. Rollback here = re-map checkout, unmap green—the old app is still running, untouched.
cf unmap-route checkout-green apps.example.com --hostname checkout-test
cf delete checkout -f
cf rename checkout-green checkout                     # rotation: live is `checkout` again
```

Why the rotation is load-bearing: without it, the second run pushes onto the app serving production.
`--no-route` does **not** unbind routes an app already holds. *[sourced:
docs.cloudfoundry.org/devguide/deploy-apps/manifest-attributes.html]* Rollback before the rotation is
route re-mapping; after `cf delete`, rollback is a fresh push of the previous artifact.

> **[unverified] Manifest-name interaction.** The example manifest pins `name: checkout`; cf CLI v7+
> may reject or reinterpret `cf push checkout-green -f manifest.yml` when the manifest names a
> different app. This exact interaction has not been exercised on a real foundation. Before approving
> the playbook, the human release owner must either create a reviewed `manifest-green.yml` stanza/file
> naming `checkout-green`, or run the exact command on a bounded non-production foundation and attach
> its output. Until that real-foundation evidence exists, do not label the command `[verified]` and do
> not use it for production.

## Built-in strategies (lower-risk changes)

```bash
cf push checkout -f manifest.yml --strategy rolling
cf push checkout -f manifest.yml --strategy canary
cf continue-deployment checkout
cf cancel-deployment checkout
```

Support for canary and revisions varies by cf CLI/CAPI version and foundation configuration. It is
`[unverified]` for the target until the human release owner records version and non-production output.
Revisions do not capture routes, service bindings, or scale; cancelling a deployment is not rollback.

> **Revisions capture less than people assume.** A revision holds a droplet, a start command, and
> environment variables—not routes, service bindings, or scale.
>
> - The effective rollback window is bounded by retained staged droplets, even when more revision
>   records exist. *[sourced: Cloud Foundry application revisions documentation]*
> - `cf rollback` deploys a new revision; it does not rewind history.
> - Cancelling an in-flight deployment does not guarantee zero downtime and does not revert
>   environment-variable or service-binding changes. *[sourced: cf CLI deployment documentation]*

## Config changes & scaling

```bash
cf set-env checkout KEY value && cf restart checkout
cf set-env checkout JBP_CONFIG_X value && cf restage checkout
cf scale checkout -i 5
cf scale checkout -m 2G -k 2G
```

These are planning examples, never agent execution authority. The human release owner selects only the
approved command. Runtime-only variables generally need restart; staging/buildpack variables generally
need restage. The exact consumer and target behavior remains `[unverified]` until evidenced.

The blanket restage tip is conservative because the CLI cannot know who consumes a variable. Runtime
application settings take effect at container start; buildpack settings are consumed while staging the
droplet. The plan must name which category applies before choosing restart versus restage.

## Verify every deploy

After cutover, record traffic, errors, latency, and saturation; abort on error-rate or latency
regression, missing telemetry, or failed health checks. Also record `cf app checkout`, route mappings,
the deployed artifact identity, and the human actor's result. Preserve `[verified]`, `[sourced]`, and
`[unverified]` labels through the handoff; never upgrade a claim because it crossed a gate.

## Tip

`cf push` changes the running app lifecycle. A plan without current human release-owner approval
evidence, an exact manifest diff, health criteria, and a proven rollback path is blocked.
