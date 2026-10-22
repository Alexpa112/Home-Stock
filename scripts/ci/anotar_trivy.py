#!/usr/bin/env python3
"""Vuelca los hallazgos de un informe JSON de Trivy como anotaciones de
GitHub Actions (::error), para poder leerlos desde la API sin bajar el log."""
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    informe = json.load(f)

for resultado in informe.get("Results") or []:
    destino = resultado.get("Target", "?")
    for v in resultado.get("Vulnerabilities") or []:
        print(
            "::error::TRIVY {sev} {id} {pkg} {inst} -> {fix} [{tgt}] {ruta}".format(
                sev=v.get("Severity"),
                id=v.get("VulnerabilityID"),
                pkg=v.get("PkgName"),
                inst=v.get("InstalledVersion"),
                fix=v.get("FixedVersion"),
                tgt=destino,
                ruta=v.get("PkgPath") or (v.get("PkgIdentifier") or {}).get("PURL"),
            )[:400]
        )

# Donde vive cada copia de urllib3 (para saber cual arrastra la version vulnerable).
for resultado in informe.get("Results") or []:
    for p in resultado.get("Packages") or []:
        if p.get("Name") == "urllib3":
            print("::error::PKG urllib3 {v} {ruta}".format(
                v=p.get("Version"), ruta=p.get("FilePath") or p.get("Identifier", {}).get("PURL"))[:400])
