# Application consolidation — initial recovery inventory

## Objective
Build the real cumulative Mexico City Field Guide, retaining prior historical content and functioning features. No more replacement micro-prototypes.

## Source artifacts recovered in ChatGPT Library
- cdmx-rich-cultural-atlas-v68-evidence-workbench.zip
- cdmx-historian-interface-v79.zip
- cdmx-historian-v81-roma-condesa-pilot.zip
- Version 92–97 cumulative research archives and canonical Version 97 SQLite in the separate research-persistence branch
- Ciudad Viva Teotihuacan interactive HTML and latest cultural-atlas preview

## Confirmed state
- The main GitHub branch deploys the original app from cdmx-fieldguide-redesign.zip.
- The recent /preview/atlas/ site is a standalone reduced implementation, not a cumulative successor to the earlier ZIP app.
- The research-persistence branch contains canonical V97 SQLite and staged archaeological evidence; app integration is not complete.

## Integration rules
1. Do not replace the original app or publish another shallow preview as a release.
2. Recover and compare the application source files, screens, modules, and content across versions 68, 79, 81, and the GitHub original.
3. Preserve content and working features unless a change is documented and intentional.
4. Treat research provenance and editorial readiness separately from visual design.
5. Implement History, Places, and Field experiences as different views of shared evidence-backed content.
6. Require navigable real content, no empty sections, functional tests, and content-regression accounting before production release.

## Current limitations
The recovered ZIPs are accessible in the working container, but their internal source comparison and merge have not yet been completed. This report is an initial inventory, not a claim of full recovery or finished app.

## Next concrete work
Extract and diff the three recovered archives against the original GitHub app, identify the richest historical content and existing components, and integrate into this branch. Keep main untouched until reviewed.
