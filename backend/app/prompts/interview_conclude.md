You are evaluating whether an interview topic has been sufficiently covered.

Topic: {topic_question}
Current summary: {refined_summary}
Number of turns so far: {turn_number}

A topic is sufficiently covered ONLY when ALL of the following are true:
- The core process or concept has been explained clearly
- At least one concrete real-world example has been provided
- At least one edge case, exception, or limitation has been mentioned
- The SME's specific role or experience with this topic is clear

If any of the above is missing, output CONTINUE.
Only output CONCLUDE when all four criteria are met.

Output only one word: CONTINUE or CONCLUDE
