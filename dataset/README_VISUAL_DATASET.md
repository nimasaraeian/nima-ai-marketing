# Visual Trust Image Dataset

This folder contains a **local image dataset** for training a custom visual trust model.
Images are not tracked here by default – only the structure and documentation.

## Trust Levels (Classes)

- **high_trust**: Professional, credible, clean visuals. Clear layout, good typography, consistent branding, and a sense of polish that increases trust.
- **medium_trust**: Average design with mixed signals. Some elements look credible, but there may be small issues (clutter, weak hierarchy, generic stock photos) that reduce confidence.
- **low_trust**: Spammy, low-quality, or confusing visuals. Aggressive colors, too many flashing elements, low-resolution graphics, fake-looking UI, or layouts that feel scammy or chaotic.

## How to Add Images

1. Take screenshots of **real ads or landing pages** that you want to analyze.
2. Manually place each image into one of the three folders based on its visual trust level:

   - `images/high_trust/`
   - `images/medium_trust/`
   - `images/low_trust/`

3. Try to be consistent with your labeling criteria. Over time, this dataset will be used to train and refine the visual trust model used by the AI marketing / behavioral engine.


