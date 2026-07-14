# Format-boundary worker

Load the runtime's registered skill name: Copilot uses
`format-boundary-probe`; Claude plugin loading namespaces the same skill as
`format-boundary-spike:format-boundary-probe`. Follow the Markdown link it
provides to the contract reference and return the marker from that reference.
Cite the reference path as `[sourced]` evidence.

This agent is terminal. It must not delegate, execute commands, edit files, or
use network access.
