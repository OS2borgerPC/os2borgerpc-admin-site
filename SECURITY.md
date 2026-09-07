
# OS2BorgerPC security policies

The development team is strongly committed to responsible reporting and disclosure of security-related issues. As such, we’ve adopted and follow a set of policies which conform to that ideal and are geared toward allowing us to deliver timely security updates to the official distribution of OS2BorgerPC.

## Reporting security issues

**Short version: please report security issues by emailing os2borgerpc@os2.eu.**

If you discover security issues in **OS2BorgerPC** or related projects under the same
organization, we request you to disclose these in a *responsible* way by e-mailing to
os2borgerpc@os2.eu.

It is extremely useful if you have a reproducible test case and/or clear steps on how to
reproduce the vulnerability.

Please do not report security issues on the public Github issue tracker, as this makes
it visible which exploits exist before a fix is available, potentially comprising a lot
of unprotected instances.

Once you’ve submitted an issue via email, you should receive an acknowledgment from the product governance team as soon as possible, and depending on the action to be taken, you may receive further followup emails.

## Timeline of the process

OS2BorgerPC has a steering group, coordinating group and 1 or more vendors of which all members must response in the event of security issues. 

1. The recipients of the report first validate if there is indeed a (possible) issue.

2. After validation, we confirm that we received the report and if it is indeed a valid issue.

3. We have a private forum accessible to the technical staff. In this
   forum, an issue is created for the vulnerability where the impact and possible
   solutions are discussed.

4. The next step is to create a (draft) Github security advisory, which is only visible
   to the repository administrators and development group. Severity and impact
   will be established here.

5. If appropriate, we request a [`CVE identifier`](https://www.cve.org/ReportRequest/ReportRequestForNonCNAs).

6. A patch is implemented, reviewed and tested in a private fork.

7. During the patch development process, known service providers are contacted to
   inform them of the vulnerability and coordinate the release date and rollout of the
   fix.

8. When the fix is tested and release coordination is done, the fix is merged into the
   primary repository. The security advisory and release are published. Service providers
   update their managed instances.

9. The release and security vulnerability are communicated to the community. This
   includes a message to the OS2BorgerPC mailing list and announcements on [os2borgerpc.os2.eu](https://os2borgerpc.os2.eu).