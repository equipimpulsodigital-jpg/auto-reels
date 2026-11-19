### EL GANCHO (LO MÁS IMPORTANTE DEL VÍDEO)
En redes la gente decide en 1–2 segundos si sigue mirando. La primera frase (primer bloque, siempre del **narrador** o de un personaje en plena tensión) tiene que frenar el dedo.
- **Corta y potente:** 6–12 palabras, que se diga en menos de 4 segundos. La palabra más fuerte (bomba, cadáver, nadie, desaparecieron, traición…) en las primeras palabras.
- **Abre una pregunta, no la respondas:** el espectador tiene que NECESITAR saber qué pasó. Nunca adelantes el desenlace (mal: "casi mata al rey" → ya sabemos que vivió; bien: "…y el ramo caía directo hacia el rey").
- **Empieza en mitad de la acción o en el detalle más inquietante**, nunca con la fecha, el lugar ni un nombre que nadie conoce. Prohibido "Hoy os voy a hablar de...", "En este vídeo...", "¿Sabías que...?" y "Esta es la historia de...".
- **Imagen concreta, no idea abstracta:** algo que se pueda ver (un ramo de flores, una puerta cerrada por dentro, tres platos sin tocar), no "un suceso terrible".
- **Técnicas** (usa una distinta en cada uno de los 5 `hook_candidates`):
  1. *Contradicción:* "Lo encontraron todo en orden. Ese era el problema."
  2. *Dato imposible:* una cifra o un hecho que no debería ser verdad… y lo es.
  3. *Tú estabas allí:* segunda persona ("Si hubieras estado en esa boda, estarías muerto.").
  4. *En mitad de la acción:* el segundo exacto antes del desastre ("La mecha ya estaba encendida cuando el rey se asomó.").
  5. *Secreto o prohibición:* algo que se ocultó, se borró o nadie se atrevió a contar.
  Elige el mejor (el que más ganas da de ver el segundo 3) y úsalo en el primer bloque. Nunca inventes datos para que el gancho suene mejor: tiene que ser verdad.
- **La segunda frase sube la apuesta**, no da contexto: añade otro detalle inquietante o lo que estaba en juego. La fecha y el lugar van a partir del tercer bloque, o dentro de una frase con tensión ("Era 1906 y Madrid entero miraba a ese balcón.").
- **Parte 2:** empieza con el dato nuevo más fuerte de esta parte (no con un resumen) y recuerda lo anterior en media frase más adelante.
- **Plano del gancho:** el primer bloque debe ser muy visual: un `objeto` clave, un `event` o un personaje con `emotion` intensa. El montaje ya le añade un zoom de impacto y un golpe de sonido.
- **`hook_title`** (texto grande en pantalla): 2–6 palabras que **complementan** la frase, nunca la repiten. Ej.: voz "La puerta estaba cerrada por dentro…" → pantalla "¿DÓNDE ESTÁN?".

### 2. NARRADOR + PERSONAJES QUE HABLAN
El canal es una **serie de dibujos animados**: caricaturas 2D que se mueven, hablan con sincronía labial y gesticulan. Cada parte mezcla **voz en off del narrador** (fechas, lugares, contexto, cifras) con **escenas dramatizadas** en las que los protagonistas hablan entre ellos.
- Define 2–5 **personajes** (`characters`): nombre, voz del reparto y `look` (su caricatura). Los extranjeros hablan español con su acento: usa `americano`, `frances`, `italiano`, `ingles`... para personajes de ese país.
- `speaker` de cada bloque: `narrador` o el `id` del personaje que dice esa frase. Aproximadamente **la mitad de los bloques son diálogo**, en intercambios de 2–4 réplicas (plano / contraplano).
- Réplicas cortas, naturales y con emoción. Las cifras, fechas y datos duros los dice **el narrador**.
- Qué pueden decir los personajes y qué aviso va en `caption` y `youtube_description` lo marcan las reglas del canal (arriba).

### 3. CARICATURAS Y VESTUARIO
- Cada personaje es una **caricatura reconocible al instante**: combina nariz, mandíbula, barba/bigote, sombrero y colores para que dos personajes nunca se parezcan (p. ej. un pescador mayor con `gorra_plana`, `bigotazo` canoso y `jersey` azul marino frente a un oficial con `gorra_militar`, `uniforme` caqui y mandíbula `cuadrada`).
- **Vestuario fiel a la época** (`era` de la serie): `noble` con gorguera y `sombrero` para los siglos XVI-XVII; `levita` con `chistera` o `bombin` en el XIX; `tricornio` + `uniforme` verde oliva para la Guardia Civil; `toca` + `sotana` para monjas; `capa` + `corona` para reyes; `casco` + `uniforme` para soldados; `pañuelo` + `vestido` para campesinas...
- **Época actual** (`era: moderno`): `jersey`, `camisa`, `traje` o `vestido`, normalmente sin sombrero (`ninguno`), colores variados y alegres.
- Las mujeres llevan `female: true`.

### 4. PLANIFICACIÓN DE LA ANIMACIÓN
- **Muchos planos cortos:** cada bloque es un plano de **2,5–4 segundos** (6–12 palabras), y cada parte tiene **entre 12 y 14 bloques**. Cada plano muestra la acción concreta de esa frase.
- **Narrador:** alterna planos `general` del lugar (con personajes de cuerpo entero en `cast`, caminando con `walk` cuando se mueven), planos `objeto` (la carta, el arma, el mapa, el oro...) y `event` para la acción (explosiones, disparos, incendios, multitudes...). Usa el suceso o el objeto que mejor ilustre la frase.
- **Diálogo:** `framing: personaje` con `cast: [quien_habla, quien_escucha]` para plano/contraplano (el primer plano del que habla con la nuca del otro), o `dos` para verlos juntos. Elige `gesture` y `emotion` acordes a la frase y `listener_emotion` para la reacción del otro.
- Mantén el **mismo lugar** durante un intercambio de diálogo; cambia de lugar solo cuando la historia avanza. Usa `mood` (día, atardecer, noche, tormenta) para el ambiente y la tensión.
- `camera`: `push_in` para tensión, `pull_back` para revelar, `shake` en momentos violentos, `static` para pausas. Varía entre planos.
- `sfx` solo para remarcar golpes de efecto (`hit` en una revelación, `whoosh` en un giro); los sucesos ya traen su sonido.
- En `visual_direction` (español) describe en una frase qué pasa en el plano.
