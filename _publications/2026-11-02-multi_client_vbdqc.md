---
title: "Multi-Client Delegated Verifiable Blind Quantum Computing"
collection: publications
category: conferences
permalink: /publication/2026-11-02-multi_client_vbdqc
excerpt: "This project was a bigger undertaking than the results might warrant, and I learned a whole lot! After taking my first cryptography course, I was eager to explore the intersection of quantum computing and cryptographic protocols, and I am tremendously grateful for the opportunity to work alongside Rosario Gennaro as we waded into the quantum cryptography landscape. There was a lot of reading and trying to figure out the open problems in the field. Going into a newer field is daunting and there were a lot of two steps forward, one step back moments, but there really are no shortcuts in learning. I was grateful to get to present this work at ACM's PQQS 2026. I feel energized and prepared to take on a new quantum cryptography challenge."
date: 2026-11-02
authors: "Matthew Prest and Rosario Gennaro"
venue: "Post-Quantum and Quantum-based Security (PQQS '26)"
paperurl: '/files/multi_client_vbdqc.pdf'
doi: '10.1145/3839338.3857244'
---
We construct a multi-Client verifiable blind delegated quantum computing (VBDQC) protocol in which M classical Verifier Clients jointly delegate a public quantum circuit acting on their combined private inputs to two quantum-capable Provers sharing entanglement but having no direct communication channel. We begin by modifying the single-Client, entanglement-based CGJV Verifier-on-a-Leash protocol. We then prove simulator-based blind verifiability for the modified protocol using the abstract/constructive cryptography framework. We adapt the DFPR upward-reduction chain to the two-Prover setting, constructing a no-direct-communication simulator architecture. We then extend the CGJV protocol to M Clients using classical multiparty computation techniques, preserving the single-Client guarantees of completeness, soundness, and blindness while additionally guaranteeing input privacy between Clients. Security is analyzed under a threat model that allows a subset of Clients to collude with one but not both of the Provers, which do not communicate even after the protocol execution.
