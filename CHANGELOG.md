# Changelog

All notable changes to Loop are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

Releases are cut automatically by [release-please](https://github.com/googleapis/release-please)
on every merge to `main`. Each version section below is generated from
Conventional Commits (`feat:`, `fix:`, `perf:`, `refactor:`, `docs:`,
`security:`); manual edits are preserved between releases.

<!-- release-please-start -->
<!-- release-please-end -->

## [1.2.0](https://github.com/kwameasare/loop/compare/v1.1.0...v1.2.0) (2026-05-16)


### Added

* **cp,dp:** per-(principal, route) HTTP rate-limit middleware (vega [#8](https://github.com/kwameasare/loop/issues/8)) ([#231](https://github.com/kwameasare/loop/issues/231)) ([ebf000a](https://github.com/kwameasare/loop/commit/ebf000aa4f0470293be41265ab9581db4f021e03))
* **cp:** postgres-backed agent registry ([f549a27](https://github.com/kwameasare/loop/commit/f549a2718bd470ec50c765180f715f6883233a5a))
* **cp:** postgres-backed agent registry ([645c78d](https://github.com/kwameasare/loop/commit/645c78d452d240696e1a1eb44683d4254e3cfb7a))
* **cp:** postgres-backed api-key service ([86eb26b](https://github.com/kwameasare/loop/commit/86eb26b25559df873b7d99db9166486d821388e4))
* **cp:** postgres-backed api-key service ([d8ab6a5](https://github.com/kwameasare/loop/commit/d8ab6a5e869b9b55c77748f7efe0cc159a7110cc))
* **cp:** postgres-backed audit_event store ([19f1f3e](https://github.com/kwameasare/loop/commit/19f1f3ed40e664ba52a80878bf3834252a9f6b0a))
* **cp:** postgres-backed audit_event store ([41916d6](https://github.com/kwameasare/loop/commit/41916d680c81bce12a6ef4a99545d44930b8b79f))
* **cp:** postgres-backed refresh_token store ([4716eac](https://github.com/kwameasare/loop/commit/4716eac47f399f1263755b527b15df33e337258f))
* **cp:** postgres-backed refresh_token store ([5fc1ecd](https://github.com/kwameasare/loop/commit/5fc1ecdadb4e0997f63b34f576fa18822b00d846))
* **cp:** postgres-backed workspace service ([1eed3d6](https://github.com/kwameasare/loop/commit/1eed3d640eff161a7840f5baf1d3fac9067b05c0))
* **cp:** postgres-backed workspace service ([8ee98d6](https://github.com/kwameasare/loop/commit/8ee98d687e0e0cbf19c3efc1e7663a2758931dab))
* **cp:** RS256/JWKS JWT verifier (vega [#11](https://github.com/kwameasare/loop/issues/11)) ([#232](https://github.com/kwameasare/loop/issues/232)) ([cfb6714](https://github.com/kwameasare/loop/commit/cfb67149e86b4d491265f8bbfb2dc1bcf1d9850a))
* **dp:** propagate SSE client disconnects into the executor (vega [#4](https://github.com/kwameasare/loop/issues/4)) ([#230](https://github.com/kwameasare/loop/issues/230)) ([c06f10b](https://github.com/kwameasare/loop/commit/c06f10badb29b8add0de2b4fa4bae9c4cf5b99bc))
* **dp:** TurnExecutionError subclass hierarchy (vega [#6](https://github.com/kwameasare/loop/issues/6)) ([#234](https://github.com/kwameasare/loop/issues/234)) ([7b95b2f](https://github.com/kwameasare/loop/commit/7b95b2f256b9db7f30675b50cb92a7032851b41d))
* **gateway:** cross-provider failover chain (vega [#3](https://github.com/kwameasare/loop/issues/3)) ([#229](https://github.com/kwameasare/loop/issues/229)) ([6d86f4e](https://github.com/kwameasare/loop/commit/6d86f4e07fd26918323f03577017cee1451297a1))
* **gateway:** Decimal cost arithmetic in providers (vega [#2](https://github.com/kwameasare/loop/issues/2)) ([#233](https://github.com/kwameasare/loop/issues/233)) ([0c1825e](https://github.com/kwameasare/loop/commit/0c1825e9eb8ed3f40e66dc13584e4700c8d3a7e2))
* **memory:** preserve source trace evidence ([#615](https://github.com/kwameasare/loop/issues/615)) ([a119261](https://github.com/kwameasare/loop/commit/a119261bc3897f0c3eebbeac887e4167a0ddaab5))
* **studio:** add glass agent aesthetic ([#639](https://github.com/kwameasare/loop/issues/639)) ([7fd28ec](https://github.com/kwameasare/loop/commit/7fd28ecc4c3fb84af63541e4e01b09a8edb5ca86))
* **studio:** surface creation intake on workbench ([#564](https://github.com/kwameasare/loop/issues/564)) ([c8b0ed8](https://github.com/kwameasare/loop/commit/c8b0ed8d5c64d0257a0e6f3f0e78ab643f063575))
* **studio:** UX005 state copy localization kit ([#245](https://github.com/kwameasare/loop/issues/245)) ([dbf91d9](https://github.com/kwameasare/loop/commit/dbf91d9bc81e13df4b45598013089e9f785f7f4d))
* **studio:** UX006 canonical shell smoke harness ([#250](https://github.com/kwameasare/loop/issues/250)) ([7af62a2](https://github.com/kwameasare/loop/commit/7af62a2576d0e4c306d1d1d50eb2d3ba7322b973))
* **studio:** UX101 agent workbench ([#257](https://github.com/kwameasare/loop/issues/257)) ([0a85c08](https://github.com/kwameasare/loop/commit/0a85c08c14bdf48506b64212bea1df67aecbd083))
* **studio:** UX102 behavior editor ([#258](https://github.com/kwameasare/loop/issues/258)) ([4996980](https://github.com/kwameasare/loop/commit/49969807feddfa779f373674848adb65ed63ec16))
* **studio:** UX103 agent map ([#259](https://github.com/kwameasare/loop/issues/259)) ([084856e](https://github.com/kwameasare/loop/commit/084856ed52b5553e7e135a0d468e7583f57a5671))
* **studio:** UX104 tools room ([#260](https://github.com/kwameasare/loop/issues/260)) ([a4e2e2f](https://github.com/kwameasare/loop/commit/a4e2e2f1ea76ef841ee5c1ac68216575973d1eed))
* **studio:** UX105 memory studio ([#261](https://github.com/kwameasare/loop/issues/261)) ([ba60968](https://github.com/kwameasare/loop/commit/ba60968a69c2def9054d445fa259bdd904393437))
* **studio:** UX106 multi-agent conductor ([#262](https://github.com/kwameasare/loop/issues/262)) ([9b83a21](https://github.com/kwameasare/loop/commit/9b83a2161e48c907d98ff3d1a7307f4ad9fe1da0))
* **studio:** UX107 build to test flow ([#263](https://github.com/kwameasare/loop/issues/263)) ([195502b](https://github.com/kwameasare/loop/commit/195502bc9e73c2b55ff36f0f597f5c394b4ebdc8))
* **studio:** UX201 simulator conversation lab ([#255](https://github.com/kwameasare/loop/issues/255)) ([45456d5](https://github.com/kwameasare/loop/commit/45456d568de4c2f1c169906a3b86c046ab192093))
* **studio:** UX202 trace theater ([#241](https://github.com/kwameasare/loop/issues/241)) ([1d690c7](https://github.com/kwameasare/loop/commit/1d690c7e5aa3e2131db835f21a8b42138925e613))
* **studio:** UX203 trace scrubber xray ([#256](https://github.com/kwameasare/loop/issues/256)) ([b878a92](https://github.com/kwameasare/loop/commit/b878a9281802ec54ff2ee14e585694c07fa64deb))
* **studio:** UX204 eval foundry ([#244](https://github.com/kwameasare/loop/issues/244)) ([0e6db42](https://github.com/kwameasare/loop/commit/0e6db42651c3ff52e9269afd26d8d47cae62b92d))
* **studio:** UX206 knowledge atelier ([#249](https://github.com/kwameasare/loop/issues/249)) ([9483708](https://github.com/kwameasare/loop/commit/94837087b3c7dad2a9c455386635b6eed980a258))
* **studio:** UX210 cost latency surfaces ([#254](https://github.com/kwameasare/loop/issues/254)) ([7a771b0](https://github.com/kwameasare/loop/commit/7a771b092005bfa738cde59633608ca18bd3ef9b))
* **studio:** UX301 Migration Atelier with first-class import + parity panes ([#242](https://github.com/kwameasare/loop/issues/242)) ([393241a](https://github.com/kwameasare/loop/commit/393241ac1ff21ede1b0c366281fea21d4800dd3f))
* **studio:** UX302 botpress parity harness + canary cutover ([#248](https://github.com/kwameasare/loop/issues/248)) ([ab804be](https://github.com/kwameasare/loop/commit/ab804be5b46a44baf2a6b80c9b02318cd967d614))
* **studio:** UX303 Deployment Flight Deck — preflight, gates, canary, rollback ([#243](https://github.com/kwameasare/loop/issues/243)) ([06796ba](https://github.com/kwameasare/loop/commit/06796baf75f1b30db6eecd873dffef827184bb34))
* **studio:** UX304 what-could-break, regression bisect, signed snapshots ([#251](https://github.com/kwameasare/loop/issues/251)) ([7742984](https://github.com/kwameasare/loop/commit/77429844dada8a2925fe513d1f9bbb3c41623127))
* **studio:** UX305 inbox HITL — evidence panes, suggested draft, resolution-to-eval ([#246](https://github.com/kwameasare/loop/issues/246)) ([b12f9c8](https://github.com/kwameasare/loop/commit/b12f9c8285bd3dd1f5b234f3e32fa60e30338b18))
* **studio:** UX306 enterprise governance overview ([#247](https://github.com/kwameasare/loop/issues/247)) ([843b903](https://github.com/kwameasare/loop/commit/843b903759b6b61124eb9e6f32a3e7f75a30da8d))
* **studio:** UX307 collaboration — presence, comments, changesets, pair debug ([#252](https://github.com/kwameasare/loop/issues/252)) ([f53e1cb](https://github.com/kwameasare/loop/commit/f53e1cb541046f29f5298b16e824acb70f043b2e))
* **studio:** UX308 AI Co-Builder — consent, provenance, diffs, Rubber Duck, Second Pair Of Eyes ([#253](https://github.com/kwameasare/loop/issues/253)) ([79c0fb7](https://github.com/kwameasare/loop/commit/79c0fb7820a4e116201a0e1b4d3dceb98b54de1b))
* **studio:** UX401 command palette, contextual find, saved searches, sharing, redaction, quick branch links ([44129de](https://github.com/kwameasare/loop/commit/44129de44ed116cfd0d07ea699b9fd7d76666934))
* **studio:** UX402 onboarding three doors, templates, spotlight, concierge ([9788d71](https://github.com/kwameasare/loop/commit/9788d7138808df92384f3ccb9938e462064826cd))
* **studio:** UX403 marketplace and private skill library ([a37fe17](https://github.com/kwameasare/loop/commit/a37fe1739febe801752ec70d362e1e7ce4fe6ac1))
* **studio:** UX404 responsive modes — mobile urgent, tablet review, second-monitor, large display ([d85e013](https://github.com/kwameasare/loop/commit/d85e013e59905101ae5bb8fa9e5a496323f47fc2))
* **studio:** UX405 a11y, i18n, color-blind & keyboard sweep ([5483722](https://github.com/kwameasare/loop/commit/5483722ff598925b76b1fb287de18da4bfda5837))
* **studio:** UX406 creative polish — earned moments, ambient life, skeletons ([7b43ae5](https://github.com/kwameasare/loop/commit/7b43ae5aeac03cacae036632538a39ab6f0babc3))
* **studio:** UX407 target UX quality bar dashboard and review checklist ([806a655](https://github.com/kwameasare/loop/commit/806a6551e1c631d9b2e24a4a1467ab98910e3ecd))
* **studio:** UX408 north-star scenario harness ([85cea23](https://github.com/kwameasare/loop/commit/85cea23c5056661a13fe81a355131f7d12245101))
* **studio:** UX409 information architecture stitching ([46096a1](https://github.com/kwameasare/loop/commit/46096a1ab136d67ba4af25c53aab273dcf113c5d))
* **traces:** derive memory spans from source evidence ([#618](https://github.com/kwameasare/loop/issues/618)) ([055f1f9](https://github.com/kwameasare/loop/commit/055f1f987fdb897307a92bb7231de7a98bed10d2))
* **traces:** surface memory evidence spans ([#616](https://github.com/kwameasare/loop/issues/616)) ([aca25a7](https://github.com/kwameasare/loop/commit/aca25a70893732ffcae7c2c64c8d7fc6bd740637))


### Fixed

* **agent-map:** quarantine target ux fixtures ([#604](https://github.com/kwameasare/loop/issues/604)) ([74c7960](https://github.com/kwameasare/loop/commit/74c7960c500fd868c7dd6753a4e7d438136a9b68))
* **agents:** expose registry operational facts ([#578](https://github.com/kwameasare/loop/issues/578)) ([305b7ca](https://github.com/kwameasare/loop/commit/305b7caa76167e6b9a87f87c568deb77430a8566))
* **agents:** expose workbench topbar facts ([#577](https://github.com/kwameasare/loop/issues/577)) ([5ff982b](https://github.com/kwameasare/loop/commit/5ff982b2f8efe43ecd5fed1398c847b52d6af48b))
* **agents:** show draft readiness checklist ([#575](https://github.com/kwameasare/loop/issues/575)) ([6be36e3](https://github.com/kwameasare/loop/commit/6be36e3e8b14bff97aa3a95567bfc6825b1568c0))
* **agents:** stop faking missing commitment documents ([#608](https://github.com/kwameasare/loop/issues/608)) ([36d0039](https://github.com/kwameasare/loop/commit/36d003942aa0e355722cf9dd5cd45ccdab1ac18a))
* **api:** document full inbox channel set ([#601](https://github.com/kwameasare/loop/issues/601)) ([f6a4c82](https://github.com/kwameasare/loop/commit/f6a4c82b70ac74488314a256137e5912a3e73822))
* **approvals:** expire requested change package reviews ([#586](https://github.com/kwameasare/loop/issues/586)) ([a922f79](https://github.com/kwameasare/loop/commit/a922f79c58b70298964b8927fa453e711531ac2f))
* **behavior:** complete selected repair loop ([#572](https://github.com/kwameasare/loop/issues/572)) ([1ebdac7](https://github.com/kwameasare/loop/commit/1ebdac7c725f10816079c90e0a13c3cdde50707f))
* **behavior:** preserve catch resolution patch ([#583](https://github.com/kwameasare/loop/issues/583)) ([4d01c9f](https://github.com/kwameasare/loop/commit/4d01c9f455d4bebf4d140876ddc1fc208ef46ca9))
* **behavior:** remove fixture build flow from editor ([#613](https://github.com/kwameasare/loop/issues/613)) ([d3d0ca0](https://github.com/kwameasare/loop/commit/d3d0ca0a5b8bf3fabc9244fb2f8125a1833645af))
* **behavior:** require repair decisions before eval save ([#612](https://github.com/kwameasare/loop/issues/612)) ([135d481](https://github.com/kwameasare/loop/commit/135d481300c6cfbe0277b6d89d37614d7ce673b2))
* **channels:** capture inbound webhook traces ([#614](https://github.com/kwameasare/loop/issues/614)) ([738a7d5](https://github.com/kwameasare/loop/commit/738a7d59bc3acfb9c80da75644b304cf8fd89fc5))
* **channels:** expose readiness contracts ([#593](https://github.com/kwameasare/loop/issues/593)) ([4451173](https://github.com/kwameasare/loop/commit/4451173f998f5a6beabf5e239eebd9b36cbdbd18))
* **channels:** record channel activity evidence ([#584](https://github.com/kwameasare/loop/issues/584)) ([9591d31](https://github.com/kwameasare/loop/commit/9591d31e4a2f3bc2d90308233fc9c3d7a7ec1815))
* **channels:** remove stale channel type narrowing ([#602](https://github.com/kwameasare/loop/issues/602)) ([9961935](https://github.com/kwameasare/loop/commit/9961935e83802a85e3ddb2ac071fc08cb32b41c5))
* **channels:** stop faking missing channel bindings ([#610](https://github.com/kwameasare/loop/issues/610)) ([6eccc35](https://github.com/kwameasare/loop/commit/6eccc35b964fe11b78af6bbc93661d489c033573))
* **channels:** wire readiness operations ([#573](https://github.com/kwameasare/loop/issues/573)) ([b0ae1a6](https://github.com/kwameasare/loop/commit/b0ae1a661ccca9d5679fe1024161c7eff4c990b2))
* **contract:** show commitment version history ([#581](https://github.com/kwameasare/loop/issues/581)) ([aa4dc49](https://github.com/kwameasare/loop/commit/aa4dc49cd1020e5eff67e367d184ea6758d0db63))
* **cost:** stop treating latency planning as live evidence ([#607](https://github.com/kwameasare/loop/issues/607)) ([dc4784d](https://github.com/kwameasare/loop/commit/dc4784d92470f057857802a89bf2b3d5d5889b70))
* **deploys:** stop faking missing change packages ([#609](https://github.com/kwameasare/loop/issues/609)) ([53461e9](https://github.com/kwameasare/loop/commit/53461e9b98ac4eaa73c7337b4e8715b827234550))
* **deploy:** target bisect from selected safety risk ([#628](https://github.com/kwameasare/loop/issues/628)) ([142a225](https://github.com/kwameasare/loop/commit/142a225ca332926f00a21678bd58193077046cbc))
* **deploy:** wire live regression bisect ([#626](https://github.com/kwameasare/loop/issues/626)) ([5d1d5bf](https://github.com/kwameasare/loop/commit/5d1d5bf550c2768c0d940594771996722650a4f3))
* **governance:** link preapproval usage evidence ([#576](https://github.com/kwameasare/loop/issues/576)) ([6bc024d](https://github.com/kwameasare/loop/commit/6bc024d8fa30f5c43534ca6f6b442cab032de9fd))
* **govern:** audit preapproved class expiry ([#587](https://github.com/kwameasare/loop/issues/587)) ([8f43324](https://github.com/kwameasare/loop/commit/8f433249fc330099caf8f3f0ee688a23176a0e33))
* **govern:** export full compliance evidence refs ([#585](https://github.com/kwameasare/loop/issues/585)) ([c4dfe79](https://github.com/kwameasare/loop/commit/c4dfe793d7ddd665dc04816a58e30124de0ed108))
* **home:** wire homepage pins ([#622](https://github.com/kwameasare/loop/issues/622)) ([ffc796c](https://github.com/kwameasare/loop/commit/ffc796c60c6594fda0d5025a292083ea37f26e7d))
* **inbox:** preserve all channel provenance ([#600](https://github.com/kwameasare/loop/issues/600)) ([dd9ed52](https://github.com/kwameasare/loop/commit/dd9ed52971e04dab93352f9258d8c6d99f1e9725))
* **inbox:** surface resolution eval workflow ([#619](https://github.com/kwameasare/loop/issues/619)) ([2d83ae6](https://github.com/kwameasare/loop/commit/2d83ae65903ac8c0bcd966f8c9760b374e7e31ef))
* **incidents:** create reports for paused rollouts ([#591](https://github.com/kwameasare/loop/issues/591)) ([8d0ba15](https://github.com/kwameasare/loop/commit/8d0ba1528cdd486e410631795f158f2302b04fa2))
* **intake:** gate incomplete contracts for clarification ([#595](https://github.com/kwameasare/loop/issues/595)) ([18883ca](https://github.com/kwameasare/loop/commit/18883caa6199d930f64d30b853c60aadf5407a78))
* **intake:** infer channels from legacy artifacts ([#590](https://github.com/kwameasare/loop/issues/590)) ([fa22437](https://github.com/kwameasare/loop/commit/fa22437060b4c593539a5e5ae7e8029a4ecbc5d6))
* **intake:** infer tools from api artifacts ([#588](https://github.com/kwameasare/loop/issues/588)) ([c87ad73](https://github.com/kwameasare/loop/commit/c87ad7368a3e62505a7a0b906eb0b9028366081f))
* **intake:** persist candidate knowledge sources ([#589](https://github.com/kwameasare/loop/issues/589)) ([a444af6](https://github.com/kwameasare/loop/commit/a444af6388084fdfb297ceb4bb7c79a96af052c1))
* **intake:** recover failed draft generation ([#596](https://github.com/kwameasare/loop/issues/596)) ([2a47e17](https://github.com/kwameasare/loop/commit/2a47e17ca3f90383c51c2bd651b9fc0278f83400))
* **intake:** require approved template provenance ([#611](https://github.com/kwameasare/loop/issues/611)) ([5391e6b](https://github.com/kwameasare/loop/commit/5391e6b0bab955d7548cfa18d0901511f4101778))
* **intake:** surface artifact recovery progress ([#597](https://github.com/kwameasare/loop/issues/597)) ([660312b](https://github.com/kwameasare/loop/commit/660312bc11a0e9b568c7bab8fb546d125211e6b5))
* **kb:** wire agent knowledge documents ([#579](https://github.com/kwameasare/loop/issues/579)) ([cc5f027](https://github.com/kwameasare/loop/commit/cc5f027661ec9bc80592240afc3f610fc29695f7))
* **memory:** expose source evidence in studio ([#617](https://github.com/kwameasare/loop/issues/617)) ([3f163a3](https://github.com/kwameasare/loop/commit/3f163a31081311ec39f7f967a5623736feb3d44d))
* **memory:** support enterprise policy scopes ([#598](https://github.com/kwameasare/loop/issues/598)) ([5713008](https://github.com/kwameasare/loop/commit/57130086313109638517fe57942600f7727a9c4b))
* **migration:** seed parity evals on import ([#594](https://github.com/kwameasare/loop/issues/594)) ([7145e1c](https://github.com/kwameasare/loop/commit/7145e1c403ea0d00a37dd797abf1fc09fc64c9e3))
* **nav:** expose pre-promote safety ([#627](https://github.com/kwameasare/loop/issues/627)) ([d4aab00](https://github.com/kwameasare/loop/commit/d4aab00e0d02aec554dfecfbc33b54e02c557feb))
* **observe:** compare anomalies against commitments ([#599](https://github.com/kwameasare/loop/issues/599)) ([bd9c660](https://github.com/kwameasare/loop/commit/bd9c660bf5f4118b1ead47d06030bf12cb443f8d))
* **observe:** derive live operating recommendation ([#580](https://github.com/kwameasare/loop/issues/580)) ([08341ea](https://github.com/kwameasare/loop/commit/08341ea72d6d20a021153221b16dd5da675a2e8e))
* **observe:** persist anomaly tasks and evals ([#592](https://github.com/kwameasare/loop/issues/592)) ([308ae3c](https://github.com/kwameasare/loop/commit/308ae3cb7685e4781590af43d28f5c90b85ee918))
* **onboarding:** wire recap and concierge to workspace data ([#621](https://github.com/kwameasare/loop/issues/621)) ([863ad96](https://github.com/kwameasare/loop/commit/863ad96b1b53f08819bc639fe685e0b051cf0260))
* **quality:** wire reports to control plane ([#620](https://github.com/kwameasare/loop/issues/620)) ([bc31355](https://github.com/kwameasare/loop/commit/bc313553f5f88de168898d75d12184f643407069))
* **scenes:** add workspace scene library ([#624](https://github.com/kwameasare/loop/issues/624)) ([9b9244b](https://github.com/kwameasare/loop/commit/9b9244be5f1016151504e7af812f955dc3a17a34))
* **shell:** mount telemetry consent gate ([#623](https://github.com/kwameasare/loop/issues/623)) ([67a6d6c](https://github.com/kwameasare/loop/commit/67a6d6cf96710c56763775e759ce261db101cd91))
* **shell:** surface pair debug audio in agent context ([#625](https://github.com/kwameasare/loop/issues/625)) ([6c5b4e3](https://github.com/kwameasare/loop/commit/6c5b4e3d180fe177d1a835c46d96f6c4c9796f37))
* **simulator:** require explicit fixture evidence ([#605](https://github.com/kwameasare/loop/issues/605)) ([db515ac](https://github.com/kwameasare/loop/commit/db515ac22b32721e820bc0c6b34b77b8a65d5e00))
* **studio:** align map copy with agent workbench ([5701dd8](https://github.com/kwameasare/loop/commit/5701dd8d3c19fad254ece44fb163bd6bc7899c25))
* **studio:** align north-star scenarios with IA routes ([#632](https://github.com/kwameasare/loop/issues/632)) ([47e2d07](https://github.com/kwameasare/loop/commit/47e2d07659031ff90755452d3cd501ed42dc3257))
* **studio:** focus deploy workbench controls ([#565](https://github.com/kwameasare/loop/issues/565)) ([b86f15f](https://github.com/kwameasare/loop/commit/b86f15fafff877da86e0b5b2ebc5d3e933cf4348))
* **studio:** focus workbench evidence links ([#560](https://github.com/kwameasare/loop/issues/560)) ([4beaeea](https://github.com/kwameasare/loop/commit/4beaeea34c8d0cc6a2339b1acbc57fa60fa44931))
* **studio:** honor inbox agent query state ([#562](https://github.com/kwameasare/loop/issues/562)) ([73b6978](https://github.com/kwameasare/loop/commit/73b6978d60234521bdfd532cee051f02b7205022))
* **studio:** honor remaining workbench query states ([#566](https://github.com/kwameasare/loop/issues/566)) ([ba82965](https://github.com/kwameasare/loop/commit/ba829657b10502ce7c480c5da261a3a9d4cc515c))
* **studio:** honor trace evidence query state ([#561](https://github.com/kwameasare/loop/issues/561)) ([2dcfc57](https://github.com/kwameasare/loop/commit/2dcfc577662ea4b22cb39d1458b3a71592008b13))
* **studio:** honor workbench evidence query panels ([#563](https://github.com/kwameasare/loop/issues/563)) ([96ff84c](https://github.com/kwameasare/loop/commit/96ff84c0df2f18bb382b5fa100fa4e5faab1e5c9))
* **studio:** keep voice under channels IA ([#630](https://github.com/kwameasare/loop/issues/630)) ([87f2ea7](https://github.com/kwameasare/loop/commit/87f2ea74b330a2f9bcae55e4b5eefc8523855071))
* **studio:** quarantine observatory fixtures ([#569](https://github.com/kwameasare/loop/issues/569)) ([8902ffa](https://github.com/kwameasare/loop/commit/8902ffa24fafe404fc48364ca87946118a483920))
* **studio:** quarantine replay workbench fixtures ([#568](https://github.com/kwameasare/loop/issues/568)) ([22c74b3](https://github.com/kwameasare/loop/commit/22c74b360dab259dc0519adf718bbdbc253f0d66))
* **studio:** remove internal fixture copy leaks ([f56121a](https://github.com/kwameasare/loop/commit/f56121a08798365e0493f7f1066d9de3154bed0f))
* **studio:** route workbench controls to durable surfaces ([#631](https://github.com/kwameasare/loop/issues/631)) ([622927b](https://github.com/kwameasare/loop/commit/622927bdc310dab5fc637b96e720abca8881b1b0))
* **studio:** wire live presence into pair debugging ([#567](https://github.com/kwameasare/loop/issues/567)) ([a274b98](https://github.com/kwameasare/loop/commit/a274b98e1139ab4ac12de9e190c14a75bc1ec428))
* **tests:** regenerate stale TS clients + bump cp_alembic head pin ([7978ae7](https://github.com/kwameasare/loop/commit/7978ae7fdf12fb2c0940636560d1f457eb70ac0e))
* **tests:** regenerate stale TS clients + bump cp_alembic head pin ([e217128](https://github.com/kwameasare/loop/commit/e217128345ff2a68edb8e7366ffc570e7a11d10c))
* **tests:** rename colliding test_verify.py files per-channel ([07c1f25](https://github.com/kwameasare/loop/commit/07c1f25523254ff23f7a3b296be7d04b5a82fd34))
* **tests:** rename colliding test_verify.py files per-channel ([8b54ff0](https://github.com/kwameasare/loop/commit/8b54ff05b070e66a4e936e483c44ca08c162cfb5))
* **tools:** wire tool telemetry metrics ([#582](https://github.com/kwameasare/loop/issues/582)) ([2f1801d](https://github.com/kwameasare/loop/commit/2f1801d8cacece08e7d41bff26354889d36a53cd))
* **trace:** ground insight controls in trace evidence ([#603](https://github.com/kwameasare/loop/issues/603)) ([d0e3be0](https://github.com/kwameasare/loop/commit/d0e3be09b1cac4e5ccb5a1ba7f3ed118d4a19b02))
* **voice:** require real provider provisioning outside deterministic mode ([#629](https://github.com/kwameasare/loop/issues/629)) ([9a0d2b3](https://github.com/kwameasare/loop/commit/9a0d2b3493641c0237c0ad657f8cb84c8a525eea))
* **voice:** wire provisioned numbers into stage ([#571](https://github.com/kwameasare/loop/issues/571)) ([eec13dc](https://github.com/kwameasare/loop/commit/eec13dc1aac0abedd125650ca6c6a2f0f7fbc80f))
* **workbench:** require explicit ux fixtures ([#606](https://github.com/kwameasare/loop/issues/606)) ([2ec91df](https://github.com/kwameasare/loop/commit/2ec91df67bc88a17175ebef99d550f5bd92419ab))
* **workflow:** wire release candidate gate controls ([#574](https://github.com/kwameasare/loop/issues/574)) ([9390cd0](https://github.com/kwameasare/loop/commit/9390cd053048c7b38e2d8da66f3c7e1122127fd5))


### Documentation

* **cloud:** update portability proof marks ([b8069a1](https://github.com/kwameasare/loop/commit/b8069a1cfc71d0326f7a394ec262a6562fb5db4e))
* **cloud:** update portability proof marks ([1c3fff4](https://github.com/kwameasare/loop/commit/1c3fff4bab5b1b0f032f84c54ce389af69caba5c))
* **cloud:** update portability proof marks ([7cf8ccc](https://github.com/kwameasare/loop/commit/7cf8cccb7eb2bd829dfb5fa10d2519b56cc07bff))
* **cloud:** update portability proof marks ([d97137c](https://github.com/kwameasare/loop/commit/d97137c2639e624f6eb25e3b771b1c1e24a072f9))
* **cloud:** update portability proof marks ([ff749e5](https://github.com/kwameasare/loop/commit/ff749e5f65406afac350fc9f7af3916b54d27e17))
* **cloud:** update portability proof marks ([31d7837](https://github.com/kwameasare/loop/commit/31d78372c6b090c9f3d24820d8fd931e7baf4e54))
* **cloud:** update portability proof marks ([5cb2af1](https://github.com/kwameasare/loop/commit/5cb2af1666b31d07423279d1c81bdb6c19fb6383))
* **cloud:** update portability proof marks ([1d22552](https://github.com/kwameasare/loop/commit/1d22552c42f5d641ad3749fe38e9072b4428e494))
* **cloud:** update portability proof marks ([607884a](https://github.com/kwameasare/loop/commit/607884a662cb2f8ebd3f6fcdd834a7e8eecbe203))
* **cloud:** update portability proof marks ([deae927](https://github.com/kwameasare/loop/commit/deae927a4fc7c4ad40d28e892bcedf85a49e1bac))
* **cloud:** update portability proof marks ([01ab1fe](https://github.com/kwameasare/loop/commit/01ab1fe3d79c3be861079abfd283f2b3e0dbabd5))
* **cloud:** update portability proof marks ([e9e0530](https://github.com/kwameasare/loop/commit/e9e053093f40551c5bb2c0b99326628dcaebd9e0))
* **p1-p2:** per-agent post-P0 assignment briefs ([0ffc868](https://github.com/kwameasare/loop/commit/0ffc868220bef2835ac600359c839e48d252be7a))
* **p1-p2:** per-agent post-P0 assignment briefs ([3f8e9c8](https://github.com/kwameasare/loop/commit/3f8e9c8885822313e044c9d6b4fc91b3f99095a9))
* **readme:** add end-to-end local-pilot bring-up ([#240](https://github.com/kwameasare/loop/issues/240)) ([4b4cbce](https://github.com/kwameasare/loop/commit/4b4cbce2e130fcc0e609461d92727bd858359f88))
* **studio:** refresh stale comment about modal a11y (thor [#4](https://github.com/kwameasare/loop/issues/4)) ([#238](https://github.com/kwameasare/loop/issues/238)) ([f286fca](https://github.com/kwameasare/loop/commit/f286fca7807c69a483b29ee8853ec195fdab0998))

## [1.1.0](https://github.com/kwameasare/loop/compare/v1.0.0...v1.1.0) (2026-05-13)


### Added

* **cp,dp:** per-(principal, route) HTTP rate-limit middleware (vega [#8](https://github.com/kwameasare/loop/issues/8)) ([#231](https://github.com/kwameasare/loop/issues/231)) ([ebf000a](https://github.com/kwameasare/loop/commit/ebf000aa4f0470293be41265ab9581db4f021e03))
* **cp:** inbound webhook dispatcher — final P0.4 group ([b83d118](https://github.com/kwameasare/loop/commit/b83d11840eee4b607262b79ce2d61120e3d43dd1))
* **cp:** postgres-backed agent registry ([f549a27](https://github.com/kwameasare/loop/commit/f549a2718bd470ec50c765180f715f6883233a5a))
* **cp:** postgres-backed agent registry ([645c78d](https://github.com/kwameasare/loop/commit/645c78d452d240696e1a1eb44683d4254e3cfb7a))
* **cp:** postgres-backed api-key service ([86eb26b](https://github.com/kwameasare/loop/commit/86eb26b25559df873b7d99db9166486d821388e4))
* **cp:** postgres-backed api-key service ([d8ab6a5](https://github.com/kwameasare/loop/commit/d8ab6a5e869b9b55c77748f7efe0cc159a7110cc))
* **cp:** postgres-backed audit_event store ([19f1f3e](https://github.com/kwameasare/loop/commit/19f1f3ed40e664ba52a80878bf3834252a9f6b0a))
* **cp:** postgres-backed audit_event store ([41916d6](https://github.com/kwameasare/loop/commit/41916d680c81bce12a6ef4a99545d44930b8b79f))
* **cp:** postgres-backed refresh_token store ([4716eac](https://github.com/kwameasare/loop/commit/4716eac47f399f1263755b527b15df33e337258f))
* **cp:** postgres-backed refresh_token store ([5fc1ecd](https://github.com/kwameasare/loop/commit/5fc1ecdadb4e0997f63b34f576fa18822b00d846))
* **cp:** postgres-backed workspace service ([1eed3d6](https://github.com/kwameasare/loop/commit/1eed3d640eff161a7840f5baf1d3fac9067b05c0))
* **cp:** postgres-backed workspace service ([8ee98d6](https://github.com/kwameasare/loop/commit/8ee98d687e0e0cbf19c3efc1e7663a2758931dab))
* **cp:** RS256/JWKS JWT verifier (vega [#11](https://github.com/kwameasare/loop/issues/11)) ([#232](https://github.com/kwameasare/loop/issues/232)) ([cfb6714](https://github.com/kwameasare/loop/commit/cfb67149e86b4d491265f8bbfb2dc1bcf1d9850a))
* **dp:** propagate SSE client disconnects into the executor (vega [#4](https://github.com/kwameasare/loop/issues/4)) ([#230](https://github.com/kwameasare/loop/issues/230)) ([c06f10b](https://github.com/kwameasare/loop/commit/c06f10badb29b8add0de2b4fa4bae9c4cf5b99bc))
* **dp:** TurnExecutionError subclass hierarchy (vega [#6](https://github.com/kwameasare/loop/issues/6)) ([#234](https://github.com/kwameasare/loop/issues/234)) ([7b95b2f](https://github.com/kwameasare/loop/commit/7b95b2f256b9db7f30675b50cb92a7032851b41d))
* **gateway:** cross-provider failover chain (vega [#3](https://github.com/kwameasare/loop/issues/3)) ([#229](https://github.com/kwameasare/loop/issues/229)) ([6d86f4e](https://github.com/kwameasare/loop/commit/6d86f4e07fd26918323f03577017cee1451297a1))
* **gateway:** Decimal cost arithmetic in providers (vega [#2](https://github.com/kwameasare/loop/issues/2)) ([#233](https://github.com/kwameasare/loop/issues/233)) ([0c1825e](https://github.com/kwameasare/loop/commit/0c1825e9eb8ed3f40e66dc13584e4700c8d3a7e2))
* **memory:** preserve source trace evidence ([#615](https://github.com/kwameasare/loop/issues/615)) ([a119261](https://github.com/kwameasare/loop/commit/a119261bc3897f0c3eebbeac887e4167a0ddaab5))
* **studio:** add 401 interceptor + AuthProvider production gate ([2c49854](https://github.com/kwameasare/loop/commit/2c498545493ea67c1982130641fd2fe4df39fe5d))
* **studio:** add glass agent aesthetic ([#639](https://github.com/kwameasare/loop/issues/639)) ([7fd28ec](https://github.com/kwameasare/loop/commit/7fd28ecc4c3fb84af63541e4e01b09a8edb5ca86))
* **studio:** add section loading/error states + eval-suite create form ([4f9c414](https://github.com/kwameasare/loop/commit/4f9c414a84030c5d44638fab5c459d65aaed55a4))
* **studio:** build workspace member-management UI ([78b39a0](https://github.com/kwameasare/loop/commit/78b39a05de2be1cadbf3aed05fd98ebc1e54e66c))
* **studio:** close P0.3 — replace 9 fixture pages, add 401 interceptor, members UI ([7f41f15](https://github.com/kwameasare/loop/commit/7f41f152fc6ca6f462c6c8c2c4f787b7888a60e4))
* **studio:** surface creation intake on workbench ([#564](https://github.com/kwameasare/loop/issues/564)) ([c8b0ed8](https://github.com/kwameasare/loop/commit/c8b0ed8d5c64d0257a0e6f3f0e78ab643f063575))
* **studio:** UX005 state copy localization kit ([#245](https://github.com/kwameasare/loop/issues/245)) ([dbf91d9](https://github.com/kwameasare/loop/commit/dbf91d9bc81e13df4b45598013089e9f785f7f4d))
* **studio:** UX006 canonical shell smoke harness ([#250](https://github.com/kwameasare/loop/issues/250)) ([7af62a2](https://github.com/kwameasare/loop/commit/7af62a2576d0e4c306d1d1d50eb2d3ba7322b973))
* **studio:** UX101 agent workbench ([#257](https://github.com/kwameasare/loop/issues/257)) ([0a85c08](https://github.com/kwameasare/loop/commit/0a85c08c14bdf48506b64212bea1df67aecbd083))
* **studio:** UX102 behavior editor ([#258](https://github.com/kwameasare/loop/issues/258)) ([4996980](https://github.com/kwameasare/loop/commit/49969807feddfa779f373674848adb65ed63ec16))
* **studio:** UX103 agent map ([#259](https://github.com/kwameasare/loop/issues/259)) ([084856e](https://github.com/kwameasare/loop/commit/084856ed52b5553e7e135a0d468e7583f57a5671))
* **studio:** UX104 tools room ([#260](https://github.com/kwameasare/loop/issues/260)) ([a4e2e2f](https://github.com/kwameasare/loop/commit/a4e2e2f1ea76ef841ee5c1ac68216575973d1eed))
* **studio:** UX105 memory studio ([#261](https://github.com/kwameasare/loop/issues/261)) ([ba60968](https://github.com/kwameasare/loop/commit/ba60968a69c2def9054d445fa259bdd904393437))
* **studio:** UX106 multi-agent conductor ([#262](https://github.com/kwameasare/loop/issues/262)) ([9b83a21](https://github.com/kwameasare/loop/commit/9b83a2161e48c907d98ff3d1a7307f4ad9fe1da0))
* **studio:** UX107 build to test flow ([#263](https://github.com/kwameasare/loop/issues/263)) ([195502b](https://github.com/kwameasare/loop/commit/195502bc9e73c2b55ff36f0f597f5c394b4ebdc8))
* **studio:** UX201 simulator conversation lab ([#255](https://github.com/kwameasare/loop/issues/255)) ([45456d5](https://github.com/kwameasare/loop/commit/45456d568de4c2f1c169906a3b86c046ab192093))
* **studio:** UX202 trace theater ([#241](https://github.com/kwameasare/loop/issues/241)) ([1d690c7](https://github.com/kwameasare/loop/commit/1d690c7e5aa3e2131db835f21a8b42138925e613))
* **studio:** UX203 trace scrubber xray ([#256](https://github.com/kwameasare/loop/issues/256)) ([b878a92](https://github.com/kwameasare/loop/commit/b878a9281802ec54ff2ee14e585694c07fa64deb))
* **studio:** UX204 eval foundry ([#244](https://github.com/kwameasare/loop/issues/244)) ([0e6db42](https://github.com/kwameasare/loop/commit/0e6db42651c3ff52e9269afd26d8d47cae62b92d))
* **studio:** UX206 knowledge atelier ([#249](https://github.com/kwameasare/loop/issues/249)) ([9483708](https://github.com/kwameasare/loop/commit/94837087b3c7dad2a9c455386635b6eed980a258))
* **studio:** UX210 cost latency surfaces ([#254](https://github.com/kwameasare/loop/issues/254)) ([7a771b0](https://github.com/kwameasare/loop/commit/7a771b092005bfa738cde59633608ca18bd3ef9b))
* **studio:** UX301 Migration Atelier with first-class import + parity panes ([#242](https://github.com/kwameasare/loop/issues/242)) ([393241a](https://github.com/kwameasare/loop/commit/393241ac1ff21ede1b0c366281fea21d4800dd3f))
* **studio:** UX302 botpress parity harness + canary cutover ([#248](https://github.com/kwameasare/loop/issues/248)) ([ab804be](https://github.com/kwameasare/loop/commit/ab804be5b46a44baf2a6b80c9b02318cd967d614))
* **studio:** UX303 Deployment Flight Deck — preflight, gates, canary, rollback ([#243](https://github.com/kwameasare/loop/issues/243)) ([06796ba](https://github.com/kwameasare/loop/commit/06796baf75f1b30db6eecd873dffef827184bb34))
* **studio:** UX304 what-could-break, regression bisect, signed snapshots ([#251](https://github.com/kwameasare/loop/issues/251)) ([7742984](https://github.com/kwameasare/loop/commit/77429844dada8a2925fe513d1f9bbb3c41623127))
* **studio:** UX305 inbox HITL — evidence panes, suggested draft, resolution-to-eval ([#246](https://github.com/kwameasare/loop/issues/246)) ([b12f9c8](https://github.com/kwameasare/loop/commit/b12f9c8285bd3dd1f5b234f3e32fa60e30338b18))
* **studio:** UX306 enterprise governance overview ([#247](https://github.com/kwameasare/loop/issues/247)) ([843b903](https://github.com/kwameasare/loop/commit/843b903759b6b61124eb9e6f32a3e7f75a30da8d))
* **studio:** UX307 collaboration — presence, comments, changesets, pair debug ([#252](https://github.com/kwameasare/loop/issues/252)) ([f53e1cb](https://github.com/kwameasare/loop/commit/f53e1cb541046f29f5298b16e824acb70f043b2e))
* **studio:** UX308 AI Co-Builder — consent, provenance, diffs, Rubber Duck, Second Pair Of Eyes ([#253](https://github.com/kwameasare/loop/issues/253)) ([79c0fb7](https://github.com/kwameasare/loop/commit/79c0fb7820a4e116201a0e1b4d3dceb98b54de1b))
* **studio:** UX401 command palette, contextual find, saved searches, sharing, redaction, quick branch links ([44129de](https://github.com/kwameasare/loop/commit/44129de44ed116cfd0d07ea699b9fd7d76666934))
* **studio:** UX402 onboarding three doors, templates, spotlight, concierge ([9788d71](https://github.com/kwameasare/loop/commit/9788d7138808df92384f3ccb9938e462064826cd))
* **studio:** UX403 marketplace and private skill library ([a37fe17](https://github.com/kwameasare/loop/commit/a37fe1739febe801752ec70d362e1e7ce4fe6ac1))
* **studio:** UX404 responsive modes — mobile urgent, tablet review, second-monitor, large display ([d85e013](https://github.com/kwameasare/loop/commit/d85e013e59905101ae5bb8fa9e5a496323f47fc2))
* **studio:** UX405 a11y, i18n, color-blind & keyboard sweep ([5483722](https://github.com/kwameasare/loop/commit/5483722ff598925b76b1fb287de18da4bfda5837))
* **studio:** UX406 creative polish — earned moments, ambient life, skeletons ([7b43ae5](https://github.com/kwameasare/loop/commit/7b43ae5aeac03cacae036632538a39ab6f0babc3))
* **studio:** UX407 target UX quality bar dashboard and review checklist ([806a655](https://github.com/kwameasare/loop/commit/806a6551e1c631d9b2e24a4a1467ab98910e3ecd))
* **studio:** UX408 north-star scenario harness ([85cea23](https://github.com/kwameasare/loop/commit/85cea23c5056661a13fe81a355131f7d12245101))
* **studio:** UX409 information architecture stitching ([46096a1](https://github.com/kwameasare/loop/commit/46096a1ab136d67ba4af25c53aab273dcf113c5d))
* **studio:** wire billing/enterprise/voice/tools/inspector against cp-api ([9c6f2a8](https://github.com/kwameasare/loop/commit/9c6f2a87b5c0b0354aceb9aa15f27c41a9da8278))
* **studio:** wire inbox/costs/traces pages against real cp-api ([6ed3050](https://github.com/kwameasare/loop/commit/6ed30509aeedbb74f400e51046ac84fc7e2fefb2))
* **traces:** derive memory spans from source evidence ([#618](https://github.com/kwameasare/loop/issues/618)) ([055f1f9](https://github.com/kwameasare/loop/commit/055f1f987fdb897307a92bb7231de7a98bed10d2))
* **traces:** surface memory evidence spans ([#616](https://github.com/kwameasare/loop/issues/616)) ([aca25a7](https://github.com/kwameasare/loop/commit/aca25a70893732ffcae7c2c64c8d7fc6bd740637))


### Fixed

* **agent-map:** quarantine target ux fixtures ([#604](https://github.com/kwameasare/loop/issues/604)) ([74c7960](https://github.com/kwameasare/loop/commit/74c7960c500fd868c7dd6753a4e7d438136a9b68))
* **agents:** expose registry operational facts ([#578](https://github.com/kwameasare/loop/issues/578)) ([305b7ca](https://github.com/kwameasare/loop/commit/305b7caa76167e6b9a87f87c568deb77430a8566))
* **agents:** expose workbench topbar facts ([#577](https://github.com/kwameasare/loop/issues/577)) ([5ff982b](https://github.com/kwameasare/loop/commit/5ff982b2f8efe43ecd5fed1398c847b52d6af48b))
* **agents:** show draft readiness checklist ([#575](https://github.com/kwameasare/loop/issues/575)) ([6be36e3](https://github.com/kwameasare/loop/commit/6be36e3e8b14bff97aa3a95567bfc6825b1568c0))
* **agents:** stop faking missing commitment documents ([#608](https://github.com/kwameasare/loop/issues/608)) ([36d0039](https://github.com/kwameasare/loop/commit/36d003942aa0e355722cf9dd5cd45ccdab1ac18a))
* **api:** document full inbox channel set ([#601](https://github.com/kwameasare/loop/issues/601)) ([f6a4c82](https://github.com/kwameasare/loop/commit/f6a4c82b70ac74488314a256137e5912a3e73822))
* **approvals:** expire requested change package reviews ([#586](https://github.com/kwameasare/loop/issues/586)) ([a922f79](https://github.com/kwameasare/loop/commit/a922f79c58b70298964b8927fa453e711531ac2f))
* **behavior:** complete selected repair loop ([#572](https://github.com/kwameasare/loop/issues/572)) ([1ebdac7](https://github.com/kwameasare/loop/commit/1ebdac7c725f10816079c90e0a13c3cdde50707f))
* **behavior:** preserve catch resolution patch ([#583](https://github.com/kwameasare/loop/issues/583)) ([4d01c9f](https://github.com/kwameasare/loop/commit/4d01c9f455d4bebf4d140876ddc1fc208ef46ca9))
* **behavior:** remove fixture build flow from editor ([#613](https://github.com/kwameasare/loop/issues/613)) ([d3d0ca0](https://github.com/kwameasare/loop/commit/d3d0ca0a5b8bf3fabc9244fb2f8125a1833645af))
* **behavior:** require repair decisions before eval save ([#612](https://github.com/kwameasare/loop/issues/612)) ([135d481](https://github.com/kwameasare/loop/commit/135d481300c6cfbe0277b6d89d37614d7ce673b2))
* **channels:** capture inbound webhook traces ([#614](https://github.com/kwameasare/loop/issues/614)) ([738a7d5](https://github.com/kwameasare/loop/commit/738a7d59bc3acfb9c80da75644b304cf8fd89fc5))
* **channels:** expose readiness contracts ([#593](https://github.com/kwameasare/loop/issues/593)) ([4451173](https://github.com/kwameasare/loop/commit/4451173f998f5a6beabf5e239eebd9b36cbdbd18))
* **channels:** record channel activity evidence ([#584](https://github.com/kwameasare/loop/issues/584)) ([9591d31](https://github.com/kwameasare/loop/commit/9591d31e4a2f3bc2d90308233fc9c3d7a7ec1815))
* **channels:** remove stale channel type narrowing ([#602](https://github.com/kwameasare/loop/issues/602)) ([9961935](https://github.com/kwameasare/loop/commit/9961935e83802a85e3ddb2ac071fc08cb32b41c5))
* **channels:** stop faking missing channel bindings ([#610](https://github.com/kwameasare/loop/issues/610)) ([6eccc35](https://github.com/kwameasare/loop/commit/6eccc35b964fe11b78af6bbc93661d489c033573))
* **channels:** wire readiness operations ([#573](https://github.com/kwameasare/loop/issues/573)) ([b0ae1a6](https://github.com/kwameasare/loop/commit/b0ae1a661ccca9d5679fe1024161c7eff4c990b2))
* **contract:** show commitment version history ([#581](https://github.com/kwameasare/loop/issues/581)) ([aa4dc49](https://github.com/kwameasare/loop/commit/aa4dc49cd1020e5eff67e367d184ea6758d0db63))
* **cost:** stop treating latency planning as live evidence ([#607](https://github.com/kwameasare/loop/issues/607)) ([dc4784d](https://github.com/kwameasare/loop/commit/dc4784d92470f057857802a89bf2b3d5d5889b70))
* **deploys:** stop faking missing change packages ([#609](https://github.com/kwameasare/loop/issues/609)) ([53461e9](https://github.com/kwameasare/loop/commit/53461e9b98ac4eaa73c7337b4e8715b827234550))
* **deploy:** target bisect from selected safety risk ([#628](https://github.com/kwameasare/loop/issues/628)) ([142a225](https://github.com/kwameasare/loop/commit/142a225ca332926f00a21678bd58193077046cbc))
* **deploy:** wire live regression bisect ([#626](https://github.com/kwameasare/loop/issues/626)) ([5d1d5bf](https://github.com/kwameasare/loop/commit/5d1d5bf550c2768c0d940594771996722650a4f3))
* **governance:** link preapproval usage evidence ([#576](https://github.com/kwameasare/loop/issues/576)) ([6bc024d](https://github.com/kwameasare/loop/commit/6bc024d8fa30f5c43534ca6f6b442cab032de9fd))
* **govern:** audit preapproved class expiry ([#587](https://github.com/kwameasare/loop/issues/587)) ([8f43324](https://github.com/kwameasare/loop/commit/8f433249fc330099caf8f3f0ee688a23176a0e33))
* **govern:** export full compliance evidence refs ([#585](https://github.com/kwameasare/loop/issues/585)) ([c4dfe79](https://github.com/kwameasare/loop/commit/c4dfe793d7ddd665dc04816a58e30124de0ed108))
* **home:** wire homepage pins ([#622](https://github.com/kwameasare/loop/issues/622)) ([ffc796c](https://github.com/kwameasare/loop/commit/ffc796c60c6594fda0d5025a292083ea37f26e7d))
* **inbox:** preserve all channel provenance ([#600](https://github.com/kwameasare/loop/issues/600)) ([dd9ed52](https://github.com/kwameasare/loop/commit/dd9ed52971e04dab93352f9258d8c6d99f1e9725))
* **inbox:** surface resolution eval workflow ([#619](https://github.com/kwameasare/loop/issues/619)) ([2d83ae6](https://github.com/kwameasare/loop/commit/2d83ae65903ac8c0bcd966f8c9760b374e7e31ef))
* **incidents:** create reports for paused rollouts ([#591](https://github.com/kwameasare/loop/issues/591)) ([8d0ba15](https://github.com/kwameasare/loop/commit/8d0ba1528cdd486e410631795f158f2302b04fa2))
* **intake:** gate incomplete contracts for clarification ([#595](https://github.com/kwameasare/loop/issues/595)) ([18883ca](https://github.com/kwameasare/loop/commit/18883caa6199d930f64d30b853c60aadf5407a78))
* **intake:** infer channels from legacy artifacts ([#590](https://github.com/kwameasare/loop/issues/590)) ([fa22437](https://github.com/kwameasare/loop/commit/fa22437060b4c593539a5e5ae7e8029a4ecbc5d6))
* **intake:** infer tools from api artifacts ([#588](https://github.com/kwameasare/loop/issues/588)) ([c87ad73](https://github.com/kwameasare/loop/commit/c87ad7368a3e62505a7a0b906eb0b9028366081f))
* **intake:** persist candidate knowledge sources ([#589](https://github.com/kwameasare/loop/issues/589)) ([a444af6](https://github.com/kwameasare/loop/commit/a444af6388084fdfb297ceb4bb7c79a96af052c1))
* **intake:** recover failed draft generation ([#596](https://github.com/kwameasare/loop/issues/596)) ([2a47e17](https://github.com/kwameasare/loop/commit/2a47e17ca3f90383c51c2bd651b9fc0278f83400))
* **intake:** require approved template provenance ([#611](https://github.com/kwameasare/loop/issues/611)) ([5391e6b](https://github.com/kwameasare/loop/commit/5391e6b0bab955d7548cfa18d0901511f4101778))
* **intake:** surface artifact recovery progress ([#597](https://github.com/kwameasare/loop/issues/597)) ([660312b](https://github.com/kwameasare/loop/commit/660312bc11a0e9b568c7bab8fb546d125211e6b5))
* **kb:** wire agent knowledge documents ([#579](https://github.com/kwameasare/loop/issues/579)) ([cc5f027](https://github.com/kwameasare/loop/commit/cc5f027661ec9bc80592240afc3f610fc29695f7))
* **memory:** expose source evidence in studio ([#617](https://github.com/kwameasare/loop/issues/617)) ([3f163a3](https://github.com/kwameasare/loop/commit/3f163a31081311ec39f7f967a5623736feb3d44d))
* **memory:** support enterprise policy scopes ([#598](https://github.com/kwameasare/loop/issues/598)) ([5713008](https://github.com/kwameasare/loop/commit/57130086313109638517fe57942600f7727a9c4b))
* **migration:** seed parity evals on import ([#594](https://github.com/kwameasare/loop/issues/594)) ([7145e1c](https://github.com/kwameasare/loop/commit/7145e1c403ea0d00a37dd797abf1fc09fc64c9e3))
* **nav:** expose pre-promote safety ([#627](https://github.com/kwameasare/loop/issues/627)) ([d4aab00](https://github.com/kwameasare/loop/commit/d4aab00e0d02aec554dfecfbc33b54e02c557feb))
* **observe:** compare anomalies against commitments ([#599](https://github.com/kwameasare/loop/issues/599)) ([bd9c660](https://github.com/kwameasare/loop/commit/bd9c660bf5f4118b1ead47d06030bf12cb443f8d))
* **observe:** derive live operating recommendation ([#580](https://github.com/kwameasare/loop/issues/580)) ([08341ea](https://github.com/kwameasare/loop/commit/08341ea72d6d20a021153221b16dd5da675a2e8e))
* **observe:** persist anomaly tasks and evals ([#592](https://github.com/kwameasare/loop/issues/592)) ([308ae3c](https://github.com/kwameasare/loop/commit/308ae3cb7685e4781590af43d28f5c90b85ee918))
* **onboarding:** wire recap and concierge to workspace data ([#621](https://github.com/kwameasare/loop/issues/621)) ([863ad96](https://github.com/kwameasare/loop/commit/863ad96b1b53f08819bc639fe685e0b051cf0260))
* **quality:** wire reports to control plane ([#620](https://github.com/kwameasare/loop/issues/620)) ([bc31355](https://github.com/kwameasare/loop/commit/bc313553f5f88de168898d75d12184f643407069))
* **scenes:** add workspace scene library ([#624](https://github.com/kwameasare/loop/issues/624)) ([9b9244b](https://github.com/kwameasare/loop/commit/9b9244be5f1016151504e7af812f955dc3a17a34))
* **shell:** mount telemetry consent gate ([#623](https://github.com/kwameasare/loop/issues/623)) ([67a6d6c](https://github.com/kwameasare/loop/commit/67a6d6cf96710c56763775e759ce261db101cd91))
* **shell:** surface pair debug audio in agent context ([#625](https://github.com/kwameasare/loop/issues/625)) ([6c5b4e3](https://github.com/kwameasare/loop/commit/6c5b4e3d180fe177d1a835c46d96f6c4c9796f37))
* **simulator:** require explicit fixture evidence ([#605](https://github.com/kwameasare/loop/issues/605)) ([db515ac](https://github.com/kwameasare/loop/commit/db515ac22b32721e820bc0c6b34b77b8a65d5e00))
* **studio:** align map copy with agent workbench ([5701dd8](https://github.com/kwameasare/loop/commit/5701dd8d3c19fad254ece44fb163bd6bc7899c25))
* **studio:** align north-star scenarios with IA routes ([#632](https://github.com/kwameasare/loop/issues/632)) ([47e2d07](https://github.com/kwameasare/loop/commit/47e2d07659031ff90755452d3cd501ed42dc3257))
* **studio:** focus deploy workbench controls ([#565](https://github.com/kwameasare/loop/issues/565)) ([b86f15f](https://github.com/kwameasare/loop/commit/b86f15fafff877da86e0b5b2ebc5d3e933cf4348))
* **studio:** focus workbench evidence links ([#560](https://github.com/kwameasare/loop/issues/560)) ([4beaeea](https://github.com/kwameasare/loop/commit/4beaeea34c8d0cc6a2339b1acbc57fa60fa44931))
* **studio:** honor inbox agent query state ([#562](https://github.com/kwameasare/loop/issues/562)) ([73b6978](https://github.com/kwameasare/loop/commit/73b6978d60234521bdfd532cee051f02b7205022))
* **studio:** honor remaining workbench query states ([#566](https://github.com/kwameasare/loop/issues/566)) ([ba82965](https://github.com/kwameasare/loop/commit/ba829657b10502ce7c480c5da261a3a9d4cc515c))
* **studio:** honor trace evidence query state ([#561](https://github.com/kwameasare/loop/issues/561)) ([2dcfc57](https://github.com/kwameasare/loop/commit/2dcfc577662ea4b22cb39d1458b3a71592008b13))
* **studio:** honor workbench evidence query panels ([#563](https://github.com/kwameasare/loop/issues/563)) ([96ff84c](https://github.com/kwameasare/loop/commit/96ff84c0df2f18bb382b5fa100fa4e5faab1e5c9))
* **studio:** keep voice under channels IA ([#630](https://github.com/kwameasare/loop/issues/630)) ([87f2ea7](https://github.com/kwameasare/loop/commit/87f2ea74b330a2f9bcae55e4b5eefc8523855071))
* **studio:** quarantine observatory fixtures ([#569](https://github.com/kwameasare/loop/issues/569)) ([8902ffa](https://github.com/kwameasare/loop/commit/8902ffa24fafe404fc48364ca87946118a483920))
* **studio:** quarantine replay workbench fixtures ([#568](https://github.com/kwameasare/loop/issues/568)) ([22c74b3](https://github.com/kwameasare/loop/commit/22c74b360dab259dc0519adf718bbdbc253f0d66))
* **studio:** remove internal fixture copy leaks ([f56121a](https://github.com/kwameasare/loop/commit/f56121a08798365e0493f7f1066d9de3154bed0f))
* **studio:** route workbench controls to durable surfaces ([#631](https://github.com/kwameasare/loop/issues/631)) ([622927b](https://github.com/kwameasare/loop/commit/622927bdc310dab5fc637b96e720abca8881b1b0))
* **studio:** wire live presence into pair debugging ([#567](https://github.com/kwameasare/loop/issues/567)) ([a274b98](https://github.com/kwameasare/loop/commit/a274b98e1139ab4ac12de9e190c14a75bc1ec428))
* **tests:** regenerate stale TS clients + bump cp_alembic head pin ([7978ae7](https://github.com/kwameasare/loop/commit/7978ae7fdf12fb2c0940636560d1f457eb70ac0e))
* **tests:** regenerate stale TS clients + bump cp_alembic head pin ([e217128](https://github.com/kwameasare/loop/commit/e217128345ff2a68edb8e7366ffc570e7a11d10c))
* **tests:** rename colliding test_verify.py files per-channel ([07c1f25](https://github.com/kwameasare/loop/commit/07c1f25523254ff23f7a3b296be7d04b5a82fd34))
* **tests:** rename colliding test_verify.py files per-channel ([8b54ff0](https://github.com/kwameasare/loop/commit/8b54ff05b070e66a4e936e483c44ca08c162cfb5))
* **tools:** wire tool telemetry metrics ([#582](https://github.com/kwameasare/loop/issues/582)) ([2f1801d](https://github.com/kwameasare/loop/commit/2f1801d8cacece08e7d41bff26354889d36a53cd))
* **trace:** ground insight controls in trace evidence ([#603](https://github.com/kwameasare/loop/issues/603)) ([d0e3be0](https://github.com/kwameasare/loop/commit/d0e3be09b1cac4e5ccb5a1ba7f3ed118d4a19b02))
* **voice:** require real provider provisioning outside deterministic mode ([#629](https://github.com/kwameasare/loop/issues/629)) ([9a0d2b3](https://github.com/kwameasare/loop/commit/9a0d2b3493641c0237c0ad657f8cb84c8a525eea))
* **voice:** wire provisioned numbers into stage ([#571](https://github.com/kwameasare/loop/issues/571)) ([eec13dc](https://github.com/kwameasare/loop/commit/eec13dc1aac0abedd125650ca6c6a2f0f7fbc80f))
* **workbench:** require explicit ux fixtures ([#606](https://github.com/kwameasare/loop/issues/606)) ([2ec91df](https://github.com/kwameasare/loop/commit/2ec91df67bc88a17175ebef99d550f5bd92419ab))
* **workflow:** wire release candidate gate controls ([#574](https://github.com/kwameasare/loop/issues/574)) ([9390cd0](https://github.com/kwameasare/loop/commit/9390cd053048c7b38e2d8da66f3c7e1122127fd5))


### Documentation

* **cloud:** update portability proof marks ([d97137c](https://github.com/kwameasare/loop/commit/d97137c2639e624f6eb25e3b771b1c1e24a072f9))
* **cloud:** update portability proof marks ([ff749e5](https://github.com/kwameasare/loop/commit/ff749e5f65406afac350fc9f7af3916b54d27e17))
* **cloud:** update portability proof marks ([31d7837](https://github.com/kwameasare/loop/commit/31d78372c6b090c9f3d24820d8fd931e7baf4e54))
* **cloud:** update portability proof marks ([5cb2af1](https://github.com/kwameasare/loop/commit/5cb2af1666b31d07423279d1c81bdb6c19fb6383))
* **cloud:** update portability proof marks ([1d22552](https://github.com/kwameasare/loop/commit/1d22552c42f5d641ad3749fe38e9072b4428e494))
* **cloud:** update portability proof marks ([607884a](https://github.com/kwameasare/loop/commit/607884a662cb2f8ebd3f6fcdd834a7e8eecbe203))
* **cloud:** update portability proof marks ([deae927](https://github.com/kwameasare/loop/commit/deae927a4fc7c4ad40d28e892bcedf85a49e1bac))
* **cloud:** update portability proof marks ([01ab1fe](https://github.com/kwameasare/loop/commit/01ab1fe3d79c3be861079abfd283f2b3e0dbabd5))
* **cloud:** update portability proof marks ([e9e0530](https://github.com/kwameasare/loop/commit/e9e053093f40551c5bb2c0b99326628dcaebd9e0))
* **p1-p2:** per-agent post-P0 assignment briefs ([0ffc868](https://github.com/kwameasare/loop/commit/0ffc868220bef2835ac600359c839e48d252be7a))
* **p1-p2:** per-agent post-P0 assignment briefs ([3f8e9c8](https://github.com/kwameasare/loop/commit/3f8e9c8885822313e044c9d6b4fc91b3f99095a9))
* **readme:** add end-to-end local-pilot bring-up ([#240](https://github.com/kwameasare/loop/issues/240)) ([4b4cbce](https://github.com/kwameasare/loop/commit/4b4cbce2e130fcc0e609461d92727bd858359f88))
* **studio:** refresh stale comment about modal a11y (thor [#4](https://github.com/kwameasare/loop/issues/4)) ([#238](https://github.com/kwameasare/loop/issues/238)) ([f286fca](https://github.com/kwameasare/loop/commit/f286fca7807c69a483b29ee8853ec195fdab0998))

## [Unreleased]

### Added

- _Nothing yet — open a PR with a Conventional Commit title to land here._

## [1.0.0] — 2025-09-30

The first generally-available release of Loop. Stable APIs, SOC 2 Type 2
controls, and a published [docs site](https://docs.loop.example).

### Added

- **Studio**: workspaces, agents, channels, evals, traces, cost dashboard,
  audit-log viewer, BYO-Vault config UI, enterprise-SSO setup form.
- **Gateway**: OpenAI-compatible inference gateway with multi-provider
  routing, retries with budgets, per-tenant rate limits, and offline-eval
  hooks.
- **Eval harness**: golden tests, regression budgets, Pareto-front
  comparisons, JUnit reporters, CI-friendly canary deploy.
- **Memory**: short-term, episodic, and long-term tiers with vector and
  scalar indexes; pluggable KB engine.
- **Tool host**: sandboxed tool execution with PII redaction and audit
  events.
- **Voice + phone**: provisioned numbers, low-latency voice agents.
- **Channels**: Slack, web chat, SMS, voice, email adapters.
- **Control plane**: workspaces, members, roles, SSO (SAML, OIDC), SCIM,
  audit-log export, data-deletion (GDPR Art. 17), BYO-Vault, regional
  deploys, DR runbooks.
- **Docs site**: docs.loop.example v1 with quickstart and three tutorials,
  reviewed by three design partners (S659).
- **Accessibility**: WCAG 2.1 AA gate on the top-10 studio pages (S656).

### Security

- SOC 2 Type 2 controls (S606–S618).
- Audit events for every workspace mutation; INSERT-only RLS on the
  `audit_events` table (S630, S632).
- BYO-Vault credential rotation runbook (S637, RB-024).

### Documentation

- Full architecture corpus under `loop_implementation/` (ADRs, API spec,
  data schema, security, runbooks, performance benchmarks).
- Public docs at <https://docs.loop.example>.

[Unreleased]: https://github.com/kwameasare/loop/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/kwameasare/loop/releases/tag/v1.0.0
