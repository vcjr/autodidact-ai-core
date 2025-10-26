# PROMPT FOR AI AGENT: Generate Subdomains for Learning Domains

You are helping to create a hierarchical learning taxonomy for an autodidact education platform. I have a list of 217 top-level learning domains. Your task is to identify which domains are broad enough to warrant subdomains and then generate those subdomains.

## CONTEXT

The current schema has domains with this structure:
```json
{
  "id": "MUSIC",
  "description": "Instrument performance, theory, composition, and audio production."
}
```

## YOUR TASK

1. Review the provided list of 217 domains
2. Identify domains that are expansive enough to have meaningful subdomains (typically 3+ distinct subdisciplines)
3. For each identified domain, create 5-15 subdomains that represent specific, learnable subdisciplines
4. Output a NEW JSON structure that includes a `subdomains` array for applicable domains

## CRITERIA FOR DOMAINS THAT NEED SUBDOMAINS

- The domain covers multiple distinct disciplines (e.g., MUSIC has piano, guitar, drums, theory, production)
- Each subdomain should be specific enough to be a focused learning path
- Subdomains should be mutually exclusive where possible (minimal overlap)
- Each subdomain should be substantial enough to require dedicated learning (not just a single skill)

## NAMING CONVENTIONS

- Parent domain ID: `MUSIC`
- Subdomain ID: `MUSIC_PIANO`, `MUSIC_GUITAR`, `MUSIC_THEORY`, etc.
- Use snake_case with UPPERCASE
- Subdomain IDs should include the parent domain prefix

## DESIRED OUTPUT SCHEMA

```json
[
  {
    "id": "MUSIC",
    "description": "Instrument performance, theory, composition, and audio production.",
    "subdomains": [
      {
        "id": "MUSIC_PIANO",
        "description": "Piano technique, sight-reading, classical and contemporary repertoire."
      },
      {
        "id": "MUSIC_GUITAR",
        "description": "Acoustic and electric guitar, fingerstyle, strumming, and soloing."
      },
      {
        "id": "MUSIC_DRUMS",
        "description": "Percussion technique, rhythm, rudiments, and kit drumming."
      },
      {
        "id": "MUSIC_VOICE",
        "description": "Vocal technique, breathing, pitch control, and performance."
      },
      {
        "id": "MUSIC_THEORY",
        "description": "Harmony, scales, chord progressions, and musical analysis."
      },
      {
        "id": "MUSIC_COMPOSITION",
        "description": "Songwriting, arrangement, orchestration, and creative process."
      },
      {
        "id": "MUSIC_PRODUCTION",
        "description": "DAWs, mixing, mastering, and electronic music creation."
      },
      {
        "id": "MUSIC_BASS",
        "description": "Bass guitar and upright bass technique, groove, and theory."
      },
      {
        "id": "MUSIC_STRINGS",
        "description": "Violin, viola, cello, and orchestral string techniques."
      },
      {
        "id": "MUSIC_BRASS",
        "description": "Trumpet, trombone, horn, and brass performance techniques."
      },
      {
        "id": "MUSIC_WOODWINDS",
        "description": "Flute, clarinet, saxophone, and woodwind performance."
      },
      {
        "id": "MUSIC_ELECTRONIC",
        "description": "Synthesizers, MIDI, electronic composition, and sound design."
      }
    ]
  },
  {
    "id": "CODING_SOFTWARE",
    "description": "Programming languages, software architecture, and application development.",
    "subdomains": [
      {
        "id": "CODING_PYTHON",
        "description": "Python programming, scripting, automation, and frameworks like Django/Flask."
      },
      {
        "id": "CODING_JAVASCRIPT",
        "description": "JavaScript, TypeScript, Node.js, and modern ECMAScript features."
      },
      {
        "id": "CODING_WEB_FRONTEND",
        "description": "HTML, CSS, React, Vue, Angular, responsive design, and user interfaces."
      },
      {
        "id": "CODING_WEB_BACKEND",
        "description": "Server-side development, REST APIs, GraphQL, databases, and microservices."
      },
      {
        "id": "CODING_MOBILE_DEV",
        "description": "iOS (Swift), Android (Kotlin), React Native, Flutter mobile development."
      },
      {
        "id": "CODING_DEVOPS",
        "description": "CI/CD, Docker, Kubernetes, infrastructure as code, and cloud deployment."
      },
      {
        "id": "CODING_JAVA",
        "description": "Java programming, Spring framework, enterprise applications, and JVM."
      },
      {
        "id": "CODING_CSHARP",
        "description": "C# programming, .NET framework, ASP.NET, and Unity development."
      },
      {
        "id": "CODING_CPP",
        "description": "C++ programming, systems programming, game engines, and performance optimization."
      },
      {
        "id": "CODING_RUST",
        "description": "Rust systems programming, memory safety, and concurrent applications."
      },
      {
        "id": "CODING_GO",
        "description": "Go programming, concurrent systems, and cloud-native applications."
      },
      {
        "id": "CODING_FUNCTIONAL",
        "description": "Functional programming with Haskell, Scala, Elixir, or F#."
      }
    ]
  },
  {
    "id": "VISUAL_ARTS",
    "description": "Drawing, painting, sculpture, and traditional art forms.",
    "subdomains": [
      {
        "id": "VISUAL_ARTS_DRAWING",
        "description": "Pencil, charcoal, ink drawing, sketching, and observational skills."
      },
      {
        "id": "VISUAL_ARTS_PAINTING",
        "description": "Oil, acrylic, watercolor painting techniques and color theory."
      },
      {
        "id": "VISUAL_ARTS_SCULPTURE",
        "description": "Clay modeling, stone carving, metal sculpture, and 3D form creation."
      },
      {
        "id": "VISUAL_ARTS_PRINTMAKING",
        "description": "Screen printing, lithography, etching, and relief printing."
      },
      {
        "id": "VISUAL_ARTS_MIXED_MEDIA",
        "description": "Collage, assemblage, and experimental mixed media techniques."
      }
    ]
  }
]
```

## EXAMPLES OF DOMAINS THAT LIKELY NEED SUBDOMAINS

- **MUSIC** → instruments (piano, guitar, drums, violin, etc.), theory, composition, production
- **CODING_SOFTWARE** → languages (Python, JavaScript, Java, C++, etc.), web frontend/backend, mobile, DevOps
- **VISUAL_ARTS** → drawing, painting, sculpture, printmaking, mixed media
- **MARTIAL_ARTS** → BJJ, Muay Thai, Karate, Judo, Taekwondo, Aikido, Wing Chun
- **ENGINEERING** → civil, mechanical, electrical, aerospace, chemical, industrial
- **MATHEMATICS** → algebra, calculus, statistics, geometry, number theory, topology
- **FOREIGN_LANGUAGE** → Spanish, Mandarin, French, German, Japanese, Arabic, etc.
- **COOKING_CULINARY** → Italian, Japanese, French, Mexican, Thai, Indian, Chinese cuisines
- **DATA_SCIENCE** → machine learning, data engineering, data visualization, statistics, NLP, computer vision
- **DIGITAL_DESIGN** → graphic design, UX design, UI design, 3D modeling, motion graphics
- **PHOTOGRAPHY** → portrait, landscape, street, wildlife, macro, commercial, editorial
- **FILM_VIDEO** → cinematography, editing, directing, color grading, screenwriting
- **SPORTS_ATHLETICS** → basketball, soccer, tennis, swimming, track & field, volleyball
- **FITNESS_TRAINING** → strength training, cardio, HIIT, bodyweight, flexibility
- **BUSINESS_MGMT** → strategy, operations, finance, marketing, HR, project management
- **PSYCHOLOGY** → cognitive, clinical, social, developmental, neuropsychology
- **CHEMISTRY** → organic, inorganic, physical, analytical, biochemistry
- **BIOLOGY** → molecular, cellular, ecology, genetics, microbiology, zoology, botany
- **PHYSICS** → classical mechanics, quantum, thermodynamics, electromagnetism, relativity
- **HISTORY** → ancient, medieval, modern, American, European, Asian, African history

## EXAMPLES OF DOMAINS THAT PROBABLY DON'T NEED SUBDOMAINS

- **SPEEDCUBING** (too specific already)
- **LOCKSMITHING** (too specific already)
- **QUILTING** (too specific already)
- **AQUARIUMS_VIVARIUMS** (specific niche)
- **GENEALOGY** (focused domain)
- **NUMISMATICS** (focused domain)

## IMPORTANT GUIDELINES

- ✅ Only add subdomains where they add genuine value for learners
- ✅ Keep subdomain descriptions clear and concise (1-2 sentences max)
- ✅ Ensure subdomains are learner-centric (what someone would actually want to study)
- ✅ Balance breadth (covering the domain) with depth (specific enough to be useful)
- ✅ Include both traditional and modern approaches where applicable
- ✅ For language domains, include the most commonly studied languages (10-15)
- ✅ For cuisine domains, include major world cuisines and techniques
- ✅ For sports, break down by individual sports or specialized training
- ✅ For arts, break down by medium or technique
- ✅ For sciences, break down by subdiscipline or specialization

## OUTPUT REQUIREMENTS

1. Return ONLY domains that have subdomains added (not all 217 domains)
2. Keep the original domain structure (id, description) and add the "subdomains" array
3. Use valid JSON format
4. Aim for 30-50 domains with subdomains (the most expansive ones)
5. Each domain should have 3-15 subdomains (average 5-8)
6. Prioritize domains where subdomains would genuinely help learners narrow their focus

## INPUT DATA

Here is the complete list of 217 domains from `domains.json`:

```json
./data/domains.json
```

## BEGIN TASK

Analyze the 217 domains above and generate subdomains for the 30-50 most expansive domains. Return only valid JSON following the schema provided.
