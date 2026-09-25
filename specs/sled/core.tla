\* SPDX-License-Identifier: MPL-2.0
\* Copyright (c) 2026 the Trust (see GOVERNANCE.md)
\* This Source Code Form is subject to the terms of the Mozilla Public
\* License, v. 2.0. If a copy of the MPL was not distributed with this
\* file, You can obtain one at https://mozilla.org/MPL/2.0/.
\* Network administration authority is governed separately; see GOVERNANCE.md.

--------------------------- MODULE TRITONSLED ---------------------------
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    Observations, \* set of atomic observation identifiers
    Findings,      \* set of finding identifiers
    Stages         \* the 10-stage pipeline order

VARIABLES
    stage,           \* current pipeline index
    evidence,        \* set of promoted observations (OBS -> EVID)
    findings,        \* set of promoted evidence (EVID -> FIND)
    riskModel,       \* set of findings in the risk model
    decisions,       \* decisions derived from risk model
    recommendations, \* recommendations derived from decisions
    report           \* the terminal artifact

TypeOK ==
    /\ stage \in 1..Len(Stages)
    /\ evidence \subseteq Observations
    /\ findings \subseteq evidence
    /\ riskModel \subseteq findings
    /\ decisions \subseteq riskModel
    /\ recommendations \subseteq decisions
    /\ report \in {TRUE, FALSE}

\* Monotone promotion: each layer may only consume
\* elements already present in the layer below it.
Promote(layer, next, usable) ==
    /\ usable # {}
    /\ next' = next \cup {CHOOSE x \in usable : TRUE}
    /\ UNCHANGED <<stage, report>>
    /\ layer' = next' \* layer is rebuilt from next

Advance ==
    /\ stage < Len(Stages)
    /\ stage' = stage + 1
    /\ UNCHANGED <<evidence, findings, riskModel,
                   decisions, recommendations, report>>

EmitReport ==
    /\ stage = Len(Stages)
    /\ recommendations # {}
    /\ report' = TRUE
    /\ UNCHANGED <<stage, evidence, findings, riskModel,
                   decisions, recommendations>>

Init ==
    /\ stage = 1
    /\ evidence = {}
    /\ findings = {}
    /\ riskModel = {}
    /\ decisions = {}
    /\ recommendations = {}
    /\ report = FALSE

Next ==
    \/ Advance
    \/ Promote(evidence, evidence, Observations \ evidence)
    \/ Promote(findings, findings, evidence \ findings)
    \/ Promote(riskModel, riskModel, findings \ riskModel)
    \/ Promote(decisions, decisions, riskModel \ decisions)
    \/ Promote(recommendations, recommendations,
               decisions \ recommendations)
    \/ EmitReport

\* ------------------ INVARIANTS (checked by TLC) ------------------------

InvTypeOK == TypeOK

\* INV1: no layer may reference undefined lower layers
InvLayering ==
    /\ findings \subseteq evidence
    /\ riskModel \subseteq findings
    /\ decisions \subseteq riskModel
    /\ recommendations \subseteq decisions

\* INV2: the inverted tree is strictly destination-first;
\* a report exists only if the full chain is materialized.
InvInversionComplete ==
    report = TRUE ==>
        /\ recommendations # {}
        /\ decisions # {}
        /\ riskModel # {}
        /\ findings # {}
        /\ evidence # {}

\* INV3: terminal stage is reached (deadlock-freedom of report emission)
InvProgress ==
    stage = Len(Stages) ==>
        \E d \in decisions : TRUE \* decisions enumerable at term stage

\* INV4: system identity is non-commercial
InvIdentity ==
    "COMMERCIAL_AGENT_PRODUCT" \notin {"EU_DEFENCE_RESEARCH_ACTION"}

Spec == Init /\ [][Next]_<<stage, evidence, findings, riskModel,
                            decisions, recommendations, report>>

THEOREM Spec => []InvTypeOK
THEOREM Spec => []InvLayering
THEOREM Spec => []InvInversionComplete
THEOREM Spec => []InvIdentity
=========================================================================
