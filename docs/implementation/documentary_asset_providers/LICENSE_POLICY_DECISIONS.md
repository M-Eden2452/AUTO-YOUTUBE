# License Policy Decisions

This document records engineering policy decisions for the documentary asset provider stage. It is not legal advice and does not claim a legal guarantee.

## Shared Defaults

- Unknown rights are blocked from automatic render.
- Missing source page is blocked.
- Missing provider asset id is blocked.
- Legacy schema records remain review-required.
- Centralized policy decisions are saved into asset manifests with policy version, provider, license name, license URL, attribution, reason and owner approval status.

## Policy Contexts

- `internal_content_production`: internal edited-video production.
- `public_multi_user_product`: future public or multi-user product context.

`internal_content_production` is the default context for the current local project pipeline. Public product use remains conservative and review-required where provider terms need a separate commercial/product audit.

## Pexels

Official references:

- https://www.pexels.com/license/
- https://www.pexels.com/terms-of-service/
- https://www.pexels.com/api/documentation/

Internal production:

- Allowed for render only when source page URL, provider asset id, download URL, provider terms URL and license URL are preserved.
- Author is preserved when returned by the API.
- Technical validation and SHA-256 are required before quality check passes.
- Standalone stock redistribution and detected prohibited use are blocked.

Public multi-user product:

- `allowed_for_render=false`
- `review_required=true`
- `owner_approval_status=commercial_audit_pending`

Future UI requirement:

- API result screens must include a prominent Pexels link and should show author when available.

## Pixabay

Official references:

- https://pixabay.com/service/license-summary/
- https://pixabay.com/service/terms/
- https://pixabay.com/api/docs/

Internal production:

- Allowed for render only when source page URL, provider asset id, download URL, provider terms URL and license URL are preserved.
- Author is preserved when returned by the API.
- Technical validation and SHA-256 are required before quality check passes.
- Standalone stock redistribution and detected prohibited use are blocked.

Public multi-user product:

- `allowed_for_render=false`
- `review_required=true`
- `owner_approval_status=commercial_audit_pending`

Future UI requirement:

- API result screens must show that results are provided by Pixabay.

## Wikimedia Commons

Official references:

- https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia
- https://commons.wikimedia.org/wiki/Commons:Licensing
- https://commons.wikimedia.org/wiki/Commons:Non-copyright_restrictions

Auto-allowed for internal production:

- Public Domain
- CC0
- CC BY 2.0
- CC BY 2.5
- CC BY 3.0
- CC BY 4.0

Required for automatic allowance:

- Source page URL.
- Exact provider page id/title.
- Exact license name.
- License URL.
- Attribution text where required.
- Author/credit for attribution licenses.
- Commercial use and modification allowed by the recognized license.
- No conflicting metadata.
- No non-copyright restriction warning that requires review.

Review-required:

- CC BY-SA.
- GFDL.
- Free Art License.
- Multiple simultaneous licenses.
- Unknown Creative Commons version.
- Missing license URL.
- Conflicting metadata.
- Unclear author.
- Unclear public-domain rationale.
- Non-copyright restrictions, personality/publicity, trademark, privacy, heraldry or coat-of-arms warnings.

Blocked:

- Unknown rights.
- Missing source/provider id/license metadata.

## NASA Image and Video Library

Official reference:

- https://www.nasa.gov/nasa-brand-center/images-and-media/

Auto-allowed for internal production:

- Documentary, editorial, educational or informational use only.
- NASA is preserved as source.
- Source page and `nasa_id` are preserved.
- No third-party copyright notice.
- No courtesy-of-third-party notice.
- No clearance warning.
- No implication that NASA endorses the channel, video or product.

Review-required:

- Identifiable persons.
- Astronauts or NASA employees where personality/publicity rights may apply.
- Third-party copyright notices.
- Courtesy-of-third-party metadata.
- NASA logos/emblems used as standalone branding.
- Promotional/advertising/merchandising context.
- Unclear ownership or metadata conflict.
- AI-generated transformation mixing NASA marks/logos with generated content.

Important:

- The provider does not mark all images.nasa.gov content as Public Domain automatically.
- Attribution export says NASA is a source and does not imply endorsement.

## Internet Archive

Official reference:

- https://help.archive.org/help/rights/

Auto-allowed:

- CC0 with explicit license URL.
- Explicit Public Domain with sufficient metadata.
- CC BY 3.0/4.0 with explicit license URL and author.
- Trusted collection rule when explicitly configured.

Review-required:

- CC BY-SA.
- Unclear Public Domain rationale.
- Missing author for attribution licenses.
- User upload without verifiable license.
- Custom rights text.
- Conflicting rights/license URL.
- Unknown collection when no explicit open license rule matches.
- Restoration/new soundtrack rights concerns.
- Identifiable people/trademarks.
- Unclear derivative file ownership.

Blocked:

- Missing license.
- All Rights Reserved.
- CC BY-NC.
- CC BY-ND.
- Borrow-only or access-restricted items.
- Copyright warning.
- Unknown rights status.

## Envato Manual Provider

Official references:

- https://help.elements.envato.com/hc/en-us/articles/360000621703-Do-any-limits-apply-to-downloads
- https://help.elements.envato.com/hc/en-us/articles/360000629006-Envato-Elements-User-Terms

Allowed only after manual import with:

- Source URL.
- Item id.
- Author.
- Local license proof/certificate reference.
- Explicit project registration confirmation.
- Technical validation.
- SHA-256.

Blocked/review-required:

- Missing source URL.
- Missing item id.
- Missing author.
- Missing license proof.
- Missing project registration confirmation.

Hard restrictions:

- No scraping.
- No automated login.
- No Playwright/Selenium/browser-bot download.
- No cookie/session extraction.
- No automated Envato download.
- License proof is stored locally under project metadata/licenses and is not published in `youtube_sources.txt`.
