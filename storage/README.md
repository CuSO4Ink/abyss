# Data Storage Layer

This layer is for inactive, dormant, bulky, historical, or not-currently-useful material.

It is hidden from the user's default information retrieval scope. Abyss should not expose this layer wholesale in prompts or daily knowledge views.

When stored material becomes relevant, Abyss should retrieve the minimal useful subset and promote or materialize it into `user_data/` with provenance.

Real archive content is ignored by Git by default. Keep only structural documentation in version control unless explicitly intended otherwise.
