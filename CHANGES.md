Changes
=======

2.2 (2022-09-30)
----------------

- Add support for stored Docker credentials with "https"-based URL
  instead of hostname as the authentication entry.


2.1 (2022-09-30)
----------------

- Add support for username/password credentials in stored Docker
  credentials in addition to identity token.


2.0 (2022-09-30)
----------------

- Add support for extracting refresh token from stored Docker
  credentials.

- Fix bug where two different repositories would not correctly get
  authorized for the destination registry.

- Added support for specifying different source and destination
  repositories. Missing blobs will be copied if necessary.


1.0 (2022-01-29)
----------------

- Initial release.
