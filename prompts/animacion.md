### 2. NARRADOR + PERSONAJES QUE HABLAN
El canal es una **serie de dibujos animados**: caricaturas 2D que se mueven, hablan con sincronía labial y gesticulan. Cada parte mezcla **voz en off del narrador** (fechas, lugares, contexto, cifras) con **escenas dramatizadas** en las que los protagonistas hablan entre ellos.
- Define 2–5 **personajes** (`characters`): nombre, voz del reparto y `look` (su caricatura). Los extranjeros hablan español con su acento: usa `americano`, `frances`, `italiano`, `ingles`... para personajes de ese país.
- `speaker` de cada bloque: `narrador` o el `id` del personaje que dice esa frase. Aproximadamente **la mitad de los bloques son diálogo**, en intercambios de 2–4 réplicas (plano / contraplano).
- **Los diálogos son una recreación**: coherentes con hechos documentados (lo que alguien hizo, vio o decidió), sin citas textuales inventadas presentadas como reales ni datos no documentados. Réplicas cortas, naturales y con emoción.
- Las cifras, fechas y datos duros los dice **el narrador**.
- En `caption` y `youtube_description` incluye siempre «Recreación animada basada en hechos reales.».

### 3. CARICATURAS Y VESTUARIO
- Cada personaje es una **caricatura reconocible al instante**: combina nariz, mandíbula, barba/bigote, sombrero y colores para que dos personajes nunca se parezcan (p. ej. un pescador mayor con `gorra_plana`, `bigotazo` canoso y `jersey` azul marino frente a un oficial con `gorra_militar`, `uniforme` caqui y mandíbula `cuadrada`).
- **Vestuario fiel a la época** (`era` de la serie): `noble` con gorguera y `sombrero` para los siglos XVI-XVII; `levita` con `chistera` o `bombin` en el XIX; `tricornio` + `uniforme` verde oliva para la Guardia Civil; `toca` + `sotana` para monjas; `capa` + `corona` para reyes; `casco` + `uniforme` para soldados; `pañuelo` + `vestido` para campesinas...
- Las mujeres llevan `female: true`.

### 4. PLANIFICACIÓN DE LA ANIMACIÓN
- **Muchos planos cortos:** cada bloque es un plano de **2,5–4 segundos** (6–12 palabras), y cada parte tiene **entre 12 y 14 bloques**. Cada plano muestra la acción concreta de esa frase.
- **Narrador:** alterna planos `general` del lugar (con personajes de cuerpo entero en `cast`, caminando con `walk` cuando se mueven), planos `objeto` (la carta, el arma, el mapa, el oro...) y `event` para la acción (explosiones, disparos, incendios, multitudes...). Usa el suceso o el objeto que mejor ilustre la frase.
- **Diálogo:** `framing: personaje` con `cast: [quien_habla, quien_escucha]` para plano/contraplano (el primer plano del que habla con la nuca del otro), o `dos` para verlos juntos. Elige `gesture` y `emotion` acordes a la frase y `listener_emotion` para la reacción del otro.
- Mantén el **mismo lugar** durante un intercambio de diálogo; cambia de lugar solo cuando la historia avanza. Usa `mood` (día, atardecer, noche, tormenta) para el ambiente y la tensión.
- `camera`: `push_in` para tensión, `pull_back` para revelar, `shake` en momentos violentos, `static` para pausas. Varía entre planos.
- `sfx` solo para remarcar golpes de efecto (`hit` en una revelación, `whoosh` en un giro); los sucesos ya traen su sonido.
- En `visual_direction` (español) describe en una frase qué pasa en el plano.
