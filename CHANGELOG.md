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

## [1.1.0](https://github.com/kwameasare/loop/compare/v1.0.0...v1.1.0) (2026-05-07)


### Added

* **audit-trail-completeness:** audit-trail completeness review (CC4.1 coverage matrix) (S581) ([#44](https://github.com/kwameasare/loop/issues/44)) ([3ef8036](https://github.com/kwameasare/loop/commit/3ef80364d2e8aebf253a6e4743d9e48c2efaa745))
* **channels-core:** inbound webhook idempotency primitives ([366edcc](https://github.com/kwameasare/loop/commit/366edcce6523bf3302a4a26d0e00ea2cd741ba6c))
* **channels-core:** inbound webhook idempotency primitives ([90cf0e8](https://github.com/kwameasare/loop/commit/90cf0e84cde19dba17a40db1246d707abff2ac64))
* **channels-discord:** ed25519 webhook signature verification ([52db0e5](https://github.com/kwameasare/loop/commit/52db0e59daed0ee1b462d1a675e0cd7a67133a75))
* **channels-discord:** ed25519 webhook signature verification ([61534fd](https://github.com/kwameasare/loop/commit/61534fd840c21ac8bd37753cef92aa77d3dd6c9e))
* **channels-email:** RFC 6376 DKIM verification on inbound MIME ([480ea4d](https://github.com/kwameasare/loop/commit/480ea4d165e21aafb29472af4eede9f89a74f7e7))
* **channels-email:** RFC 6376 DKIM verification on inbound MIME ([11621d1](https://github.com/kwameasare/loop/commit/11621d11ed979fc4378097682fdab583afbff585))
* **channels-email:** SNS message-signature verification on inbound ([0adecfa](https://github.com/kwameasare/loop/commit/0adecfa66f8af0a328a1ba864f91216dafd78c42))
* **channels-email:** SNS message-signature verification on inbound ([9a8dd1c](https://github.com/kwameasare/loop/commit/9a8dd1c2fd92cc3a345af3a90a1f13cba94f201b))
* **channels-sms:** Twilio HMAC-SHA1 webhook signature verification ([1446e87](https://github.com/kwameasare/loop/commit/1446e87fa665207d556e518b3afadf47eded9068))
* **channels-sms:** Twilio HMAC-SHA1 webhook signature verification ([6a024fb](https://github.com/kwameasare/loop/commit/6a024fbb37cda933a194dc7df3d58bd80a97419e))
* **channels-teams:** RS256 JWT verification of Bot Framework tokens ([36d9bcb](https://github.com/kwameasare/loop/commit/36d9bcbce912ccdebe30de246ec6ca780074bd9a))
* **channels-teams:** RS256 JWT verification of Bot Framework tokens ([d0683b1](https://github.com/kwameasare/loop/commit/d0683b1c21ca8102fad6ba2f997fb5c554e0df52))
* **channels:** replay-window defense for WhatsApp + Telegram inbound ([76daaa1](https://github.com/kwameasare/loop/commit/76daaa13cb6270876a765cd8a346201e12ccbc75))
* **channels:** replay-window defense for WhatsApp + Telegram inbound ([d841371](https://github.com/kwameasare/loop/commit/d8413711581a4d9cf7f3a17a82334c411c54ebf8))
* **ci:** add cross-cloud smoke matrix ([c5fec51](https://github.com/kwameasare/loop/commit/c5fec51e25ea0bf2c0601ac24b59f73ab5e879ec))
* **ci:** add cross-cloud smoke runner ([1416322](https://github.com/kwameasare/loop/commit/14163228f760fbb9048a49288c13bb0419438efe))
* **ci:** Cosign image sign and verify gate (S263) ([5aa001d](https://github.com/kwameasare/loop/commit/5aa001db1947b0f785288b8f66190df3b0586cd7))
* **ci:** wrap cross-cloud smoke runner ([11e6bd8](https://github.com/kwameasare/loop/commit/11e6bd88f206f7b8207f38c6b263ea6af4050e4a))
* **cloud:** Cloud portability proof report (S781) ([78122a4](https://github.com/kwameasare/loop/commit/78122a4b3ee8b203e467049b46cc94fc5edc106e))
* **cp-api:** add agent registry facade ([8ddc3df](https://github.com/kwameasare/loop/commit/8ddc3df777e7386d85e4ede28af6706290d1db8f))
* **cp-api:** add ASGI auth dependencies ([fe25e7d](https://github.com/kwameasare/loop/commit/fe25e7da59cbb536b72465ae672229a5a998a715))
* **cp-api:** add ASGI runtime state ([ab0e454](https://github.com/kwameasare/loop/commit/ab0e454c01920ba6556a6413c04412c19b03a8fc))
* **cp-api:** add FastAPI runtime dependencies ([a514c35](https://github.com/kwameasare/loop/commit/a514c3538443a7a2f98568a5ca8a5b27bf455997))
* **cp-api:** assemble ASGI app ([c2432ad](https://github.com/kwameasare/loop/commit/c2432adddc64139d07d86dfa364a78ffd5aa3702))
* **cp-api:** cp-api 5000 RPS gate (S845) ([4d5091e](https://github.com/kwameasare/loop/commit/4d5091eb2067c3c6fc513538242b64f7ec9cd6cc))
* **cp-api:** expose agent routes ([5940a3a](https://github.com/kwameasare/loop/commit/5940a3aea6ad1188a5d8634b9a193b9132adb6db))
* **cp-api:** expose auth exchange route ([dd97ebe](https://github.com/kwameasare/loop/commit/dd97ebed11b53e30392d7112d3cd1bddad389efc))
* **cp-api:** expose workspace routes ([fe73d5d](https://github.com/kwameasare/loop/commit/fe73d5dbbea499da712f032da3b5e33bd6e18223))
* **cp-api:** FastAPI cp-api ASGI app (S901) ([d134ea1](https://github.com/kwameasare/loop/commit/d134ea1e10d1f09a170a14da340c0563a4965580))
* **cp-api:** run ASGI app in container ([ede4509](https://github.com/kwameasare/loop/commit/ede4509c4a63ccf223ecdbb840d342002b30b8a2))
* **cp-api:** serve ASGI health routes ([9c68f92](https://github.com/kwameasare/loop/commit/9c68f9208ef2ab83fc5650d677bef4cbed3596e4))
* **cp,dp:** OpenTelemetry tracing middleware ([82fbeaf](https://github.com/kwameasare/loop/commit/82fbeafd9caa4fcea77d06a1531b950704a68e93))
* **cp,dp:** OpenTelemetry tracing middleware ([00c643e](https://github.com/kwameasare/loop/commit/00c643e3e8a54c640625d4003ff7cedb9b290dbe))
* **cp,dp:** per-(principal, route) HTTP rate-limit middleware (vega [#8](https://github.com/kwameasare/loop/issues/8)) ([#231](https://github.com/kwameasare/loop/issues/231)) ([ebf000a](https://github.com/kwameasare/loop/commit/ebf000aa4f0470293be41265ab9581db4f021e03))
* **cp,dp:** prometheus_client middleware + /metrics endpoint ([e7e4ad4](https://github.com/kwameasare/loop/commit/e7e4ad418732152caf1a304d810e47e1229e7c11))
* **cp,dp:** prometheus_client middleware + /metrics endpoint ([1fd887c](https://github.com/kwameasare/loop/commit/1fd887c1ea4880e7c3aef347460fdd72ca380cf4))
* **cp:** agent versions service + GET/POST/promote routes ([211f1e0](https://github.com/kwameasare/loop/commit/211f1e0187724f73494ee3e187693cfd35937cda))
* **cp:** agent versions service + GET/POST/promote routes ([95807f0](https://github.com/kwameasare/loop/commit/95807f07cb6b8f0962d427e9ddb119a27c6e5096))
* **cp:** conversations + takeover service + 3 routes ([65067b1](https://github.com/kwameasare/loop/commit/65067b101935a1f400c326fcbb3992ed1e5c08cf))
* **cp:** conversations + takeover service + 3 routes ([d62e147](https://github.com/kwameasare/loop/commit/d62e147e83ff33377e5fb4d45fa3fc8995486167))
* **cp:** eval suites + runs service + 4 routes ([6abe3f9](https://github.com/kwameasare/loop/commit/6abe3f989ac07d5fc00a21d9f20507a15fb1245c))
* **cp:** eval suites + runs service + 4 routes ([f694a25](https://github.com/kwameasare/loop/commit/f694a25d9b1fca5e86496b46bd62f96830bcaddb))
* **cp:** inbound webhook dispatcher — final P0.4 group ([b83d118](https://github.com/kwameasare/loop/commit/b83d11840eee4b607262b79ce2d61120e3d43dd1))
* **cp:** inbound webhook dispatcher — final P0.4 group ([dd6eed1](https://github.com/kwameasare/loop/commit/dd6eed12cdb4a9c84158b4a7b92e51ca88de576a))
* **cp:** KB document service + 4 routes ([23e6611](https://github.com/kwameasare/loop/commit/23e6611f5d76ba971d720f502d69bb50a25be5d8))
* **cp:** KB document service + 4 routes ([99c812a](https://github.com/kwameasare/loop/commit/99c812a0ae694be068c2c4356fef3a663559cb55))
* **cp:** POST /v1/auth/refresh with rotation + reuse-detection ([c32dd3c](https://github.com/kwameasare/loop/commit/c32dd3ce777df20a48ddd1a6ed465e4f9a64e974))
* **cp:** POST /v1/auth/refresh with rotation + reuse-detection ([b592414](https://github.com/kwameasare/loop/commit/b592414ae0ba636f75602d4265a9d5e5db9b6653))
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
* **cp:** wire DELETE /v1/workspaces/{id} with audit emission ([ae3b1bb](https://github.com/kwameasare/loop/commit/ae3b1bb6c454a669003202a2ced8cf52e5497bb6))
* **cp:** wire DELETE /v1/workspaces/{id} with audit emission ([869be7e](https://github.com/kwameasare/loop/commit/869be7e339963111f60042bc32c1ca7bc7429715))
* **cp:** wire GDPR Art-17 data-deletion (DSR) routes ([5e0e6bc](https://github.com/kwameasare/loop/commit/5e0e6bc52b406ae70a7a433d46e59e06cd1aedfb))
* **cp:** wire GDPR Art-17 data-deletion (DSR) routes ([cf424fa](https://github.com/kwameasare/loop/commit/cf424fae9f6b697239c1102f37768a6d3ab7d137))
* **cp:** wire trace search + usage list routes; doc remaining P0.4 gaps ([573c8f0](https://github.com/kwameasare/loop/commit/573c8f05e6ceff52f3d60f90df8c8e8a04654c7d))
* **cp:** wire trace search + usage list routes; doc remaining P0.4 gaps ([eb68896](https://github.com/kwameasare/loop/commit/eb68896375705caed82bbe167cbff373101d3e5c))
* **cp:** wire workspace API-key + secrets routes with audit emission ([bab0874](https://github.com/kwameasare/loop/commit/bab08746389c6284047f998b8e7b1b22c0444d41))
* **cp:** wire workspace API-key + secrets routes with audit emission ([890567d](https://github.com/kwameasare/loop/commit/890567da7972e94a3a24ea98a21a40e358d788d4))
* **cp:** wire workspace member CRUD routes with audit emission ([ccede26](https://github.com/kwameasare/loop/commit/ccede26079a05d6ea427706fe534d0569d49b69d))
* **cp:** wire workspace member CRUD routes with audit emission ([632f639](https://github.com/kwameasare/loop/commit/632f639b999b124ace8c1522fb74d1278bf0ff08))
* **cp:** workspace budgets service + GET/PATCH routes ([813c165](https://github.com/kwameasare/loop/commit/813c16524cf1626b99eef34c9230ee9cc295d2bf))
* **cp:** workspace budgets service + GET/PATCH routes ([3b879dc](https://github.com/kwameasare/loop/commit/3b879dcde885fc4162f4eedd3ec054dc6773f466))
* **demo:** 5 scripted demos (S914) ([#159](https://github.com/kwameasare/loop/issues/159)) ([4211b5f](https://github.com/kwameasare/loop/commit/4211b5f18411e4f1f0ebb092d52b4a002277e2cf))
* **docs:** docs.loop.example v1 Mintlify site (S915) ([#158](https://github.com/kwameasare/loop/issues/158)) ([74f93ed](https://github.com/kwameasare/loop/commit/74f93ed63a148c137abea70df47ddcaa73792542))
* **dp:** propagate SSE client disconnects into the executor (vega [#4](https://github.com/kwameasare/loop/issues/4)) ([#230](https://github.com/kwameasare/loop/issues/230)) ([c06f10b](https://github.com/kwameasare/loop/commit/c06f10badb29b8add0de2b4fa4bae9c4cf5b99bc))
* **dp:** TurnExecutionError subclass hierarchy (vega [#6](https://github.com/kwameasare/loop/issues/6)) ([#234](https://github.com/kwameasare/loop/issues/234)) ([7b95b2f](https://github.com/kwameasare/loop/commit/7b95b2f256b9db7f30675b50cb92a7032851b41d))
* **gateway:** cross-provider failover chain (vega [#3](https://github.com/kwameasare/loop/issues/3)) ([#229](https://github.com/kwameasare/loop/issues/229)) ([6d86f4e](https://github.com/kwameasare/loop/commit/6d86f4e07fd26918323f03577017cee1451297a1))
* **gateway:** Decimal cost arithmetic in providers (vega [#2](https://github.com/kwameasare/loop/issues/2)) ([#233](https://github.com/kwameasare/loop/issues/233)) ([0c1825e](https://github.com/kwameasare/loop/commit/0c1825e9eb8ed3f40e66dc13584e4700c8d3a7e2))
* **gateway:** Gateway cache hit-ratio gate (S841) ([a6113ad](https://github.com/kwameasare/loop/commit/a6113ad47f4e875a1e93b5ca94b82c3634519616))
* **gateway:** Gateway real httpx provider streams (S906) ([a4190d8](https://github.com/kwameasare/loop/commit/a4190d8e8a0de6b3ecc0037dfe624a871bcaf15a))
* **gateway:** live model catalog — stop hardcoding gpt-4o-mini ([a3d8b76](https://github.com/kwameasare/loop/commit/a3d8b761ca06bfe41b622b4ce2de67b11246fc7c))
* **gateway:** live model catalog — stop hardcoding gpt-4o-mini ([f8e71b7](https://github.com/kwameasare/loop/commit/f8e71b756a122854a6a5a90b0b414dd15353af67))
* **gateway:** live model catalog — stop hardcoding gpt-4o-mini ([8c65c2b](https://github.com/kwameasare/loop/commit/8c65c2be5495893b90b198c520d238b1272a851a))
* **helm:** Enterprise single-tenant Helm install (S638) ([55d9062](https://github.com/kwameasare/loop/commit/55d90627de3a5c03fa2689bdb379747d9e84afd5))
* **helm:** pre-install/pre-upgrade migration Job hook ([9616d9e](https://github.com/kwameasare/loop/commit/9616d9e077660b31afa6f065c522de788155db9c))
* **helm:** pre-install/pre-upgrade migration Job hook ([1f5a30d](https://github.com/kwameasare/loop/commit/1f5a30d3cd987f035119040e09b908dd2ea3ab09))
* **kb:** retrieval p50 benchmark gate (S842) ([7c39ae3](https://github.com/kwameasare/loop/commit/7c39ae3968ef542145b90e4a86c7093e1aa5de5d))
* **memory:** add LangMem retrieval ablation ([4229e96](https://github.com/kwameasare/loop/commit/4229e96e5c1afc744f50460564b375868acb125d))
* **memory:** add LangMem summarizer ([ac27423](https://github.com/kwameasare/loop/commit/ac27423f981b42a5332aef86d4eec26f88fbd962))
* **memory:** add Zep episodic store ([39d7463](https://github.com/kwameasare/loop/commit/39d74632439ecd1c4dfcb4dab71c51d0c32bf903))
* **memory:** add Zep record mapping ([37f3915](https://github.com/kwameasare/loop/commit/37f3915d0d01dcc10c7c44e14d1b2d8b3bcc99f8))
* **memory:** export Zep adapter ([4f7b25a](https://github.com/kwameasare/loop/commit/4f7b25a75110a39be5bce1e8d6210178c016c62a))
* **memory:** LangMem summary retrieval lift (S822) ([b89c6ec](https://github.com/kwameasare/loop/commit/b89c6ec906a1504568750eeeb762abc8c099c056))
* **memory:** Zep episodic memory adapter (S821) ([7956f86](https://github.com/kwameasare/loop/commit/7956f86a739852dc7498e78e26d54df62d50b49e))
* **migrations:** merge audit migration heads ([e8ac633](https://github.com/kwameasare/loop/commit/e8ac6334ba1fce925036c060abe5c5b831dabfec))
* **migrations:** Merge control-plane audit migration heads (S900) ([883f560](https://github.com/kwameasare/loop/commit/883f560a50ac14933e962dad27a1b6e103ff8347))
* **observability:** metadata-only telemetry — cross-region PII scrubber (S596) ([#38](https://github.com/kwameasare/loop/issues/38)) ([e2bcf5a](https://github.com/kwameasare/loop/commit/e2bcf5a0bc283d59b29ae217eb8defdcfe6d2481))
* **obs:** service SLO burn alerts (S805) ([dbc547a](https://github.com/kwameasare/loop/commit/dbc547ab67d6642dc58e343709fe6251f0e0ec15))
* **perf:** add OpenAI SSE perf fixture ([56a4cee](https://github.com/kwameasare/loop/commit/56a4cee714830c88634d872fd7177b7a6d073a2a))
* **perf:** add turn latency k6 gate ([e15dfd3](https://github.com/kwameasare/loop/commit/e15dfd3acfd258b85ddd22b801c49778faaed509))
* **perf:** Perf regression budget gate (S846) ([14c97e0](https://github.com/kwameasare/loop/commit/14c97e09590a990c6d7bd3c8dacd5b3341bb58cf))
* **perf:** real-image cp/runtime perf baselines (S913) ([39bee39](https://github.com/kwameasare/loop/commit/39bee39642f83cac2a4c416be6e15415df47ff72))
* **perf:** run gates on real service images ([c3c2c7f](https://github.com/kwameasare/loop/commit/c3c2c7f7dfd94e3dff4bdc88765f68f77dcc74b9))
* **portability:** add SecretsBackend contract ([71645c8](https://github.com/kwameasare/loop/commit/71645c8a7bdefd996e38ad01655e149566990325))
* **portability:** export SecretsBackend contract ([397c7b9](https://github.com/kwameasare/loop/commit/397c7b96b99f9a6807a6202b44fc492b1574054a))
* **portability:** record SecretsBackend access pattern ([5e1c3f7](https://github.com/kwameasare/loop/commit/5e1c3f76d75631cb15cca9eadce66c3b174fec7a))
* **runcsandboxfactory-behin:** RuncSandboxFactory behind SandboxFactory Protocol (S916) ([#149](https://github.com/kwameasare/loop/issues/149)) ([209249c](https://github.com/kwameasare/loop/commit/209249cd81ee58dde444cc7c8e134e24d7b545a1))
* **runtime:** add memory leak red-team harness ([e66e825](https://github.com/kwameasare/loop/commit/e66e8258e6cff7a7373702f28aba0fa583fc03e8))
* **runtime:** add memory PII redactor ([024a863](https://github.com/kwameasare/loop/commit/024a8634fa1e9d1d17a28cc682fbd054c9e29d17))
* **runtime:** add user memory isolation store ([2715380](https://github.com/kwameasare/loop/commit/27153804170e8a364561a1bc28049affde485c7f))
* **runtime:** dp-runtime FastAPI turn streaming (S902) ([36a1acc](https://github.com/kwameasare/loop/commit/36a1acc64d6ffae668700694f2d9f79d8aa19982))
* **runtime:** export memory isolation helpers ([d60cb63](https://github.com/kwameasare/loop/commit/d60cb63a49a31c8ae9f0297cd630064aac1d740d))
* **runtime:** export memory redaction helpers ([2c01954](https://github.com/kwameasare/loop/commit/2c0195474244452d7026479759117053d317068a))
* **runtime:** prioritize memory redaction spans ([52700cd](https://github.com/kwameasare/loop/commit/52700cd67d8e270f521e8cd80cebe5421d25f89e))
* **runtime:** redact memory writes per agent ([7afeafa](https://github.com/kwameasare/loop/commit/7afeafa78689738b251dfc7916e8c116b4f00d1a))
* **runtime:** Runtime 100rpm baseline report (S142) ([fdbc4a5](https://github.com/kwameasare/loop/commit/fdbc4a5dca4246678061b563176489dce29f74b4))
* **runtime:** Runtime SSE 1000-concurrency gate (S844) ([feb1d6f](https://github.com/kwameasare/loop/commit/feb1d6ff193144326061262314f5b04e5a2a0ecd))
* **runtime:** serve dp turns over FastAPI ([a85899c](https://github.com/kwameasare/loop/commit/a85899c234bef050840d66a1d75a807ee9b0cfdb))
* **s38:** close S904+S905+S917+S918+S919 + demo unblocks ([929a1ee](https://github.com/kwameasare/loop/commit/929a1ee031e9611bb0ae2b7949f020c50baeaaed))
* **s38:** close S904+S905+S917+S918+S919 + local-demo unblocks ([86b0fff](https://github.com/kwameasare/loop/commit/86b0fffb1fc2429d807880b10de2cf3d427552a6))
* **security:** Workspace CMK envelope encryption blocked on AWS sandbox (S636) ([e1e546e](https://github.com/kwameasare/loop/commit/e1e546e2333d84e68815353008923a700393b97d))
* **soc2:** S570 vanta integration auth + organization sync spec ([#30](https://github.com/kwameasare/loop/issues/30)) ([347e43b](https://github.com/kwameasare/loop/commit/347e43bb4a435f2c1294c3109358a01c41619fcf))
* **soc2:** S572 postgres PITR restore drill (RB-021) &lt;1h RTO ([#31](https://github.com/kwameasare/loop/issues/31)) ([bdbe34e](https://github.com/kwameasare/loop/commit/bdbe34edcdfe48b7e91ebc81dd5e2d5e3d1996a9))
* **soc2:** S573 clickhouse snapshot restore drill (RB-022) ([#32](https://github.com/kwameasare/loop/issues/32)) ([46f6b9c](https://github.com/kwameasare/loop/commit/46f6b9c93fe83dcd586baa4c01f84134c6b51a31))
* **soc2:** S574 objstore CRR daily integrity check (RB-023) ([#33](https://github.com/kwameasare/loop/issues/33)) ([7142fbc](https://github.com/kwameasare/loop/commit/7142fbc43bc0d4af733ead4b28f29a091a63d8f9))
* **soc2:** S575 DR tabletop record + first recorded exercise ([#34](https://github.com/kwameasare/loop/issues/34)) ([287c624](https://github.com/kwameasare/loop/commit/287c624e446ac098cb7966ae864975b93fbe5602))
* **studio:** add 401 interceptor + AuthProvider production gate ([2c49854](https://github.com/kwameasare/loop/commit/2c498545493ea67c1982130641fd2fe4df39fe5d))
* **studio:** add section loading/error states + eval-suite create form ([4f9c414](https://github.com/kwameasare/loop/commit/4f9c414a84030c5d44638fab5c459d65aaed55a4))
* **studio:** Auth0 SPA SDK wiring (S912) ([#157](https://github.com/kwameasare/loop/issues/157)) ([23ed188](https://github.com/kwameasare/loop/commit/23ed188f97bf51b4d6b6ff8037c8f158eba96874))
* **studio:** build workspace member-management UI ([78b39a0](https://github.com/kwameasare/loop/commit/78b39a05de2be1cadbf3aed05fd98ebc1e54e66c))
* **studio:** close P0.3 — replace 9 fixture pages, add 401 interceptor, members UI ([7f41f15](https://github.com/kwameasare/loop/commit/7f41f152fc6ca6f462c6c8c2c4f787b7888a60e4))
* **studio:** S212 KB management UI with upload progress + typed-confirm delete ([2a71fda](https://github.com/kwameasare/loop/commit/2a71fdafd200ce538bf7198db55e26b41ad8f3c6))
* **studio:** S253 eval suites + runs UI with regression diff ([d063d68](https://github.com/kwameasare/loop/commit/d063d6803f5f9ddc6a08beb1a470d3945526e93b))
* **studio:** S270 deploys tab with promote/pause/rollback timeline ([5f1ef48](https://github.com/kwameasare/loop/commit/5f1ef4893ad479134c8eed030e6fbb49f7a2edc6))
* **studio:** S283 workspace KPI cards (today/MTD/projected EOM) with deltas ([ad6c3a5](https://github.com/kwameasare/loop/commit/ad6c3a5c3b6570a8c8d032650e4aec50eda054e7))
* **studio:** S284 30-day cost time-series chart with agent multi-select ([ef4a2a8](https://github.com/kwameasare/loop/commit/ef4a2a87e79c769031b0d7b82e0e362d84b4ea76))
* **studio:** S288 trace list page with filters, search, pagination ([245ac5f](https://github.com/kwameasare/loop/commit/245ac5feae3d02d75c240c03b51c4bc5d9c2e159))
* **studio:** S289 SVG trace waterfall with inline attrs + 200-span perf test ([4f808ba](https://github.com/kwameasare/loop/commit/4f808ba9bd4f7ae67648a42cc562d5947ebb9c7a))
* **studio:** S306 inbox queue page with team/agent/channel filters, sort, paging ([726cff0](https://github.com/kwameasare/loop/commit/726cff0affd39f5ce76a2b739224ab28a15f0720))
* **studio:** S307 inbox conversation viewer with live SSE tail ([48b1c74](https://github.com/kwameasare/loop/commit/48b1c74ac7b10f0fc8c687b0b6c64f672ace94bb))
* **studio:** S308 takeover button + composer in conversation viewer ([f84b19c](https://github.com/kwameasare/loop/commit/f84b19cae6dd2d7091f395ea8bb5d389341229a9))
* **studio:** S309 handback button with confirmation modal and toast ([ebd041e](https://github.com/kwameasare/loop/commit/ebd041e7e04a006f37702294dcdd6f7e3d5b3895))
* **studio:** S327 billing tab with current plan, usage vs cap, Stripe portal CTA ([d59c75c](https://github.com/kwameasare/loop/commit/d59c75cd00d77410e2094b56cc9934cce0ee8575))
* **studio:** S329 billing payment-method update flow with 3DS-aware error handling ([1fcc911](https://github.com/kwameasare/loop/commit/1fcc911fee59f1abb0f536098de1a9156da28c49))
* **studio:** S384 voice channel widget with PTT and always-on modes ([b6ea4f1](https://github.com/kwameasare/loop/commit/b6ea4f1e263ca156501829d13b1a55859ffcd7cb))
* **studio:** S385 voice config tab with numbers list and ASR/TTS selectors ([4f491d7](https://github.com/kwameasare/loop/commit/4f491d782030d58a4e118ea7f63668b03d6f7d39))
* **studio:** S460 flow canvas in /agents/[agent_id]/flow with pan/zoom toolbar ([dc1d93f](https://github.com/kwameasare/loop/commit/dc1d93fb371a6a0e2d609e67c651f5ca03427284))
* **studio:** S461 flow node palette with 7 node types and drag-to-create wiring ([a584417](https://github.com/kwameasare/loop/commit/a5844178e9d992b0644275a92066af5074b6100f))
* **studio:** S462 per-type node config sidebar with blur-persist and validation ([f906cb7](https://github.com/kwameasare/loop/commit/f906cb715acd0c5a6f895afc6927737a168f3384))
* **studio:** S463 flow edge connect/click-to-delete with confirm ([39d39ff](https://github.com/kwameasare/loop/commit/39d39ff5badee8370d902760ee8ef1c5b691ce67))
* **studio:** S464 variable inspector side panel with frame timeline + diff view ([d0dc8ed](https://github.com/kwameasare/loop/commit/d0dc8ed84393ae94f882ddef7ff58ad192c2885d))
* **studio:** S467 flow YAML save/load with version_tag conflict detection ([fb19bbb](https://github.com/kwameasare/loop/commit/fb19bbbf2a24e03d184cdd7e8328683934e99e91))
* **studio:** S468 emulator panel streams /v1/turns tokens into chat preview ([6619788](https://github.com/kwameasare/loop/commit/6619788756676e4fef52c0100bd5da619717d18a))
* **studio:** S472 flow integration test — build → save → run → branch hit ([#29](https://github.com/kwameasare/loop/issues/29)) ([30e04d6](https://github.com/kwameasare/loop/commit/30e04d697197e93c363184ef11467b117e3036a1))
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
* **studio:** wire home buttons + add top nav so the app is navigable ([a1904c1](https://github.com/kwameasare/loop/commit/a1904c15c0439675d3e7eb96419df2c36dbc46bf))
* **studio:** wire home buttons + add top nav so the app is navigable ([cfb7c5f](https://github.com/kwameasare/loop/commit/cfb7c5f1a76345e3f605348dc68e75a4990ff46b))
* **studio:** wire inbox/costs/traces pages against real cp-api ([6ed3050](https://github.com/kwameasare/loop/commit/6ed30509aeedbb74f400e51046ac84fc7e2fefb2))
* **terraform:** Alibaba Cloud module static slice (S773 blocked) ([94c4ff2](https://github.com/kwameasare/loop/commit/94c4ff2b98e73a2519c43141600b3d64de928951))
* **terraform:** Hetzner cost module static slice (S775 blocked) ([98e52ea](https://github.com/kwameasare/loop/commit/98e52eaea750d2548b44c420dacb6df938cb7db1))
* **terraform:** OVHcloud sovereign module static slice (S774 blocked) ([287ea2e](https://github.com/kwameasare/loop/commit/287ea2edf529585760784991d0427485c7e69734))
* **tool-host:** Tool-host warm-start gate (S843) ([5030b92](https://github.com/kwameasare/loop/commit/5030b92d3ad9cd397190390a27e00d39fc33eeb7))
* **tools:** add missing seed_dev.py + dev.sh referenced by Makefile ([1c6d84e](https://github.com/kwameasare/loop/commit/1c6d84e7359bb5c324559fe947659cd6e036ec90))
* **tools:** add missing seed_dev.py + dev.sh referenced by Makefile ([ef23f4e](https://github.com/kwameasare/loop/commit/ef23f4e1f86ae1e2a529c7f0130eb4313d335559))
* **tracker:** close S911 ([#147](https://github.com/kwameasare/loop/issues/147)) ([26457dd](https://github.com/kwameasare/loop/commit/26457dd3e8dc27115472c2c2bf4e88adfbf6c0ad))
* **voice:** ASR TTS warm connection pool (S652) ([a3e9a98](https://github.com/kwameasare/loop/commit/a3e9a98015c8de48c535201317bc28d59a78b929))
* **voice:** Deepgram and ElevenLabs real websocket clients (S908) ([7230e69](https://github.com/kwameasare/loop/commit/7230e698260283001198257ffc9f417c3f5e80fc))
* **voice:** p50 latency benchmark gate (S654) ([b36ee8b](https://github.com/kwameasare/loop/commit/b36ee8b20876a59edc97a35ce0bf54f6a03ada6c))
* **voice:** regional endpoint selector (S653) ([812acaf](https://github.com/kwameasare/loop/commit/812acaf1b2be3d7fdda840e4153f8695eee993d6))
* **voice:** Sample-based voice perf gate (S909) ([f3dfd7d](https://github.com/kwameasare/loop/commit/f3dfd7de0e5719d7af13e84f4340e133e4a79c2d))
* **voice:** TTS prewarm sentence streaming (S651) ([149bca4](https://github.com/kwameasare/loop/commit/149bca49192a9956c2db5ab02fe8c2606d638f57))
* **voice:** Twilio live phone call harness (S910) ([3b84520](https://github.com/kwameasare/loop/commit/3b84520df9b2f201ba78c7f3bf41960d71235120))


### Fixed

* **control-plane:** swap workspace envelope crypto from XOR-stream to AES-GCM ([43873fc](https://github.com/kwameasare/loop/commit/43873fc8423d04579eb33ce9c7f11e5accb91443))
* **control-plane:** swap workspace envelope crypto from XOR-stream to AES-GCM ([d5889c1](https://github.com/kwameasare/loop/commit/d5889c1ebf19c99d863b7deb2eb8f4fb9b6515ed))
* **cp:** set version_table=cp_alembic_version to unblock cp+dp shared DB ([2ca3988](https://github.com/kwameasare/loop/commit/2ca3988deaf8566f88b3baed967d710398ce167d))
* **cp:** set version_table=cp_alembic_version to unblock shared-DB migrations ([8bd3381](https://github.com/kwameasare/loop/commit/8bd33814ee4ba76b2a7a2c6b1c8467ea1b57b954))
* **dp:** authenticate every /v1/turns request — close open-relay ([0eceeff](https://github.com/kwameasare/loop/commit/0eceeff76d03ada5b6ae6839623099003acad380))
* **dp:** authenticate every /v1/turns request — close open-relay ([b1f7ee2](https://github.com/kwameasare/loop/commit/b1f7ee2caf39ad0846b5a6c35e01509551cea245))
* **gateway:** accept bare OPENAI_API_KEY/ANTHROPIC_API_KEY as fallback ([1ed62d6](https://github.com/kwameasare/loop/commit/1ed62d629ca0303f6db7369d851d455dd413a1bf))
* **gateway:** classify -pro / -turbo / o-series as best, not balanced ([bef57af](https://github.com/kwameasare/loop/commit/bef57af61ac4b63dc439356cd8a373c234233ec3))
* **gateway:** classify -pro / -turbo / o-series as best, not balanced ([f8deaa2](https://github.com/kwameasare/loop/commit/f8deaa25111ad432c32df45671f3fbe4fb24520b))
* **gateway:** resolve discovered models via tier-fallback in cost lookup ([f94a343](https://github.com/kwameasare/loop/commit/f94a34375a3fe46e041b424c4b87b0477db1f0c3))
* **gateway:** tier-fallback in cost lookup so discovered models don't 501 ([a4764b2](https://github.com/kwameasare/loop/commit/a4764b2b338469001f616e8f96b8a16484b4d1aa))
* **helm:** pod-security hardening across all 5 service Deployments ([12e5a14](https://github.com/kwameasare/loop/commit/12e5a14b0bec0b5622f7dab0aa049aab9ce4b9f3))
* **helm:** pod-security hardening across all 5 service Deployments ([bea2723](https://github.com/kwameasare/loop/commit/bea2723eca9440751245afadaa6a789c7c12da18))
* **helm:** render component env maps as env lists ([76e3cd6](https://github.com/kwameasare/loop/commit/76e3cd67a651d53e99fa297098cfa1d675d38523))
* **infra:** release.yml builds real images, drop weak placeholder secrets ([c31621a](https://github.com/kwameasare/loop/commit/c31621ae1ab47323b32899c615ceb36b2ebb315e))
* **infra:** release.yml builds real images, drop weak placeholder secrets ([403935d](https://github.com/kwameasare/loop/commit/403935d1bfc54c97b9a456d4c44f7f9060e3dc70))
* **local:** make + docker compose actually load .env on a dev laptop ([0be88b9](https://github.com/kwameasare/loop/commit/0be88b90ea6aab599ea276d02e52ca4fcf9426c2))
* **local:** make + docker compose actually load .env on a dev laptop ([e038087](https://github.com/kwameasare/loop/commit/e0380873ac272121101bd8f634c49f5b229d1f93))
* **memory:** harden Zep record parsing ([2a8d603](https://github.com/kwameasare/loop/commit/2a8d6033aae189dae6a1d12c45f77d9f8a1e33eb))
* **memory:** preserve LangMem retrieval anchors ([41f21c3](https://github.com/kwameasare/loop/commit/41f21c3b10c82c1cda4b943c42635af952e6a22c))
* **memory:** return Zep query scores ([2d7afeb](https://github.com/kwameasare/loop/commit/2d7afebdd9e2bd04137f654c736186f212005939))
* **perf:** render runtime env map for SSE gate ([d210fbe](https://github.com/kwameasare/loop/commit/d210fbe87a1c7ba32012c07ba2868cfa8693d18b))
* **perf:** right-size runtime-sse k6 to kind-runner capacity (200 VUs) ([efbb417](https://github.com/kwameasare/loop/commit/efbb4175a2314ea4d6859f0bcaad35b0e8dca351))
* **perf:** run runtime SSE k6 inside cluster ([ccc3d44](https://github.com/kwameasare/loop/commit/ccc3d440091e6e6dc7703e73c8e0586e941c7c94))
* **perf:** scale cp-api the same way (--workers 4 + replicaCount=3) ([31237c7](https://github.com/kwameasare/loop/commit/31237c7b87f2680b3d27d22c2d97c54898c58226))
* **perf:** scale dp-runtime + uvicorn workers so 1000-SSE gate passes ([2594155](https://github.com/kwameasare/loop/commit/259415508469f0df77d7b1d9c04c6b9f6be3e888))
* **tests:** regenerate stale TS clients + bump cp_alembic head pin ([7978ae7](https://github.com/kwameasare/loop/commit/7978ae7fdf12fb2c0940636560d1f457eb70ac0e))
* **tests:** regenerate stale TS clients + bump cp_alembic head pin ([e217128](https://github.com/kwameasare/loop/commit/e217128345ff2a68edb8e7366ffc570e7a11d10c))
* **tests:** rename colliding test_verify.py files per-channel ([07c1f25](https://github.com/kwameasare/loop/commit/07c1f25523254ff23f7a3b296be7d04b5a82fd34))
* **tests:** rename colliding test_verify.py files per-channel ([8b54ff0](https://github.com/kwameasare/loop/commit/8b54ff05b070e66a4e936e483c44ca08c162cfb5))
* **test:** test_runtime_sse_1000 reflects env-overridable VUs ([6454809](https://github.com/kwameasare/loop/commit/6454809df490692061e47fbc1a5db8ab701f38a8))
* **tracker:** resolve nested merge-conflict markers in _stories_v2 + tracker.json ([#53](https://github.com/kwameasare/loop/issues/53)) ([3ddfdf6](https://github.com/kwameasare/loop/commit/3ddfdf6645ff00094b6d43aced59d50838861f00))
* **tracker:** update generated_at timestamp in tracker.json ([ca78baa](https://github.com/kwameasare/loop/commit/ca78baa594d96724c4c647be6a94153b45bad7e6))


### Documentation

* **ci:** document cross-cloud smoke paging ([63309fe](https://github.com/kwameasare/loop/commit/63309fec2643c2cf9dd19381db275d7aa7247a45))
* **cloud:** update portability proof marks ([deae927](https://github.com/kwameasare/loop/commit/deae927a4fc7c4ad40d28e892bcedf85a49e1bac))
* **cloud:** update portability proof marks ([01ab1fe](https://github.com/kwameasare/loop/commit/01ab1fe3d79c3be861079abfd283f2b3e0dbabd5))
* **cloud:** update portability proof marks ([e9e0530](https://github.com/kwameasare/loop/commit/e9e053093f40551c5bb2c0b99326628dcaebd9e0))
* **cloud:** update portability proof marks ([f9baa78](https://github.com/kwameasare/loop/commit/f9baa78b4670ce0f2ce95ef93746394f07c3171b))
* **cloud:** update portability proof marks ([80f500a](https://github.com/kwameasare/loop/commit/80f500abb03a92af8be5fd5a4d04be586c949b7b))
* **cp-api:** document ASGI routes and env ([8568904](https://github.com/kwameasare/loop/commit/8568904aaddf823820e7c83b65803dc5d290d89b))
* **cp-api:** note ASGI container wiring ([e90dbba](https://github.com/kwameasare/loop/commit/e90dbba0e0a10c42e1896613200f949f655680de))
* **memory:** document LangMem summary variant ([5d91011](https://github.com/kwameasare/loop/commit/5d91011fb6617fe1329466cf60bebc3621e6e002))
* **p1-p2:** per-agent post-P0 assignment briefs ([0ffc868](https://github.com/kwameasare/loop/commit/0ffc868220bef2835ac600359c839e48d252be7a))
* **p1-p2:** per-agent post-P0 assignment briefs ([3f8e9c8](https://github.com/kwameasare/loop/commit/3f8e9c8885822313e044c9d6b4fc91b3f99095a9))
* **perf:** document turn latency gate ([6f6866d](https://github.com/kwameasare/loop/commit/6f6866d558e6cbca2763b442a5a60ca87e923569))
* **perf:** record real-image baselines ([316d933](https://github.com/kwameasare/loop/commit/316d9333c7a821d07d66d56850ae21c668060155))
* **portability:** note SecretsBackend parity contract ([a397533](https://github.com/kwameasare/loop/commit/a3975330fb196f5e38c6cf74be8a613917bc851e))
* **readme:** add end-to-end local-pilot bring-up ([#240](https://github.com/kwameasare/loop/issues/240)) ([4b4cbce](https://github.com/kwameasare/loop/commit/4b4cbce2e130fcc0e609461d92727bd858359f88))
* **runtime:** describe dp runtime FastAPI edge ([7a66fc6](https://github.com/kwameasare/loop/commit/7a66fc623abf97f60ed815fa04446a8248020332))
* **runtime:** document dp turn service contract ([569c52e](https://github.com/kwameasare/loop/commit/569c52ef711c2c77c296c8fba53c764072346c8d))
* **runtime:** document memory PII redaction modes ([9b93e6c](https://github.com/kwameasare/loop/commit/9b93e6cbb7e0166e7503decbeaab4eb3bcbad76f))
* **runtime:** document user memory isolation audit ([5d00aee](https://github.com/kwameasare/loop/commit/5d00aee64c073d5287a3ca5189414bdf1414c5e4))
* **studio:** refresh stale comment about modal a11y (thor [#4](https://github.com/kwameasare/loop/issues/4)) ([#238](https://github.com/kwameasare/loop/issues/238)) ([f286fca](https://github.com/kwameasare/loop/commit/f286fca7807c69a483b29ee8853ec195fdab0998))
* **threat-model:** STRIDE entries for S917 + S918 + S905 ([302e1a8](https://github.com/kwameasare/loop/commit/302e1a8c06bf17dac6aae8fbd8248eca301299c0))

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
