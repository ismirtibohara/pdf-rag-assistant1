# Test results: ISDNn.pdf

Settings: top_k = 3 unless noted. Result = Correct / Partial / Wrong.

## Questions that are in the PDF

| Question | Expected | Result | Notes |
|---|---|---|---|
| What are the three categories of ISDN services? | Bearer, teleservices, supplementary. Page 2 | | |
| What is the speed of a BRI digital pipe and why? | 144 Kbps + 48 Kbps overhead = 192 Kbps. Page 1 | | |
| What do FECN and BECN do in Frame Relay? | FECN tells the destination, BECN tells the source. Page 7 | | |
| How large can the data field of a Token Bus frame be with 6-byte addresses? | 8174 bytes. Page 4 | | |
| What are the disadvantages of Frame Relay? | No error control, delay in packet transfer, less reliable. Page 8 | Correct | Right answer, cited page 8, quote is on the page |
| What is the difference between PVC and SVC? | PVC permanent, SVC temporary. Pages 7 and 8 | | |

## Questions that are NOT in the PDF (should refuse)

| Question | Expected | Result | Notes |
|---|---|---|---|
| Who won the 2018 World Cup? | "I could not find this in the document" | | |
| What is the difference between TCP and UDP? | "I could not find this in the document" | | |
| What is the maximum size of an Ethernet frame? | "I could not find this in the document" | | |

## Broad questions (known weakness)

| Question | Expected | Result | Notes |
|---|---|---|---|
| Explain this document | Overview of all 4 topics | Partial | Broad question, only 3 chunks retrieved |
| What topics does this document cover? (top_k=5) | ISDN, Token Bus, Token Ring, Frame Relay | Partial | Missed ISDN, Token Bus, Token Ring. Confidence showed 100% |

## Observations

- Broad questions fail because retrieval only returns the few chunks closest in meaning to the question.
- The model's confidence number is not reliable. It showed 100% on an incomplete answer.
- One quote joined two separate pieces of text with "...". A quote check is needed.