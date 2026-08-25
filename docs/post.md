# LinkedIn post copy

Repo link goes in the first comment, not the post body.

---

Somewhere in NASA's public archive is the raw data that first revealed seven
Earth-sized planets around TRAPPIST-1.

I pulled it myself and searched it with the same method astronomers use: no
pre-cleaned dataset, no shortcuts, just raw photometry straight from the
MAST archive.

[sync animation: simulated transit next to the real light curve dip]

Recovered six of the seven known planet periods, matched to the published
values to within 0.03%. Then ran the same pipeline on two more systems,
Kepler-90 (recovered 6 of 8 planets) and Kepler-186 (recovered all 5,
including Kepler-186f, the first Earth-size planet found in a habitable
zone).

I also trained a small CNN and a simpler feature-based model to double-check
the detections, and compared them against each other honestly: the CNN
agreed with the known answers 70% of the time. The simpler model did worse
than just guessing, and got some visually obvious transits wrong. Small
models trained on real, unaugmented data (a few dozen examples, not
thousands) don't always work, and that's worth showing, not hiding.

Then I pointed the same pipeline at 25 real, unconfirmed TESS candidates,
signals nobody has fully verified yet. My own search independently
re-detected 16 of them, and for everything flagged, worked out what kind of
planet it would actually be: size, distance from its star, temperature.

This doesn't confirm new planets, that needs follow-up observations I don't
have access to. But it's the same first step real discovery pipelines take.

Method, data, and the full repo in the comments.

---

## Notes for posting

- Open with the sync animation (`docs/figures/trappist1b_sync_animation.gif`), this is the hook.
- If a single validated number is wanted for a shorter caption instead of the full post: "0.03%" (TRAPPIST-1's
  worst-case period recovery error) is the strongest, most defensible standalone number.
- Repo link: `github.com/AmjadAAYD/exoplanet-transit-detection`, in the first comment.
