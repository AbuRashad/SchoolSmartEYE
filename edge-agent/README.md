# WAI Edge Gateway (transport-neutral scaffold)

This folder contains a **local validation-only** gateway scaffold. It does not
connect to a wristband, BLE radio, Wi-Fi device, LoRa gateway, or SchoolSmartEYE
API. No hardware model or transport has been selected.

## Requirements

- Python 3.10+
- Python standard library only (no third-party packages)

## Validate a sample locally

Create a JSON observation using the current `wai.v1` API contract, then run:

```powershell
python .\edge-agent\wai_gateway.py --validate-only --input .\sample-observation.json
```

The tool prints validation status and safe metadata only. It does not print
measurements or identifiers and does not transmit anything.

## Deliberately not implemented yet

- BLE / Wi-Fi / LoRa / other transport adapter
- Hardware-specific sensor decoding or calibration
- Device credential provisioning or storage
- Network upload / retry / offline buffering
- Claiming synthetic samples as live observations

The current server ingestion endpoint marks accepted observations
`live_unverified` and contributes to reporting coverage. Therefore this
scaffold must not send synthetic test data to that endpoint. A separate,
explicit demo-data path and server-side exclusion from live coverage must be
implemented before end-to-end simulation is enabled.

## Adapter contract

A future transport adapter must implement `TransportAdapter.receive_observation()`
and return a decoded dictionary. It may only be added after the selected
hardware's protocol, encryption, sensor semantics, firmware identity, clock,
sampling and buffering behaviour are documented and tested.

## Security requirements for the eventual live adapter

- HTTPS for non-local API endpoints.
- Load device credentials from an OS secret store or protected runtime
  environment; never commit credentials or place them in browser code.
- Never log credentials, raw student identifiers, or physiological readings.
- Respect server-side device revocation and assignment checks.
- Keep synthetic/demo traffic completely separate from live reporting.
