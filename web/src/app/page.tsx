"use client";

import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from "react";
import Link from "next/link";
import { Search, Loader2, ChevronDown, FolderOpen, Bookmark, X, Clock, Copy, Check, Sparkles, FileText, Maximize2, Settings } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, getPdfUrl } from "@/lib/api";
import { useSearch } from "@/hooks/use-search";
import type { ReferenceResult, SearchResultItem, PaperCollection, SavedSearch } from "@/lib/types";

function StanceBadge({ stance }: { stance: ReferenceResult["stance"] }) {
  if (!stance) return null;
  const styles = {
    supports: "text-green-700",
    contradicts: "text-red-700",
    neutral: "text-gray-500",
  };
  return (
    <span className={`text-xs font-medium ${styles[stance]}`}>
      {stance}
    </span>
  );
}

const CitePanel = forwardRef<{ toggle: () => void }, { paperId: string }>(function CitePanel({ paperId }, ref) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<{ short: string; full: string; bibtex: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const handleToggle = async () => {
    if (open) { setOpen(false); return; }
    setOpen(true);
    if (!data) {
      setLoading(true);
      try {
        const result = await api.papers.cite(paperId);
        setData(result);
      } catch { /* ignore */ }
      setLoading(false);
    }
  };

  useImperativeHandle(ref, () => ({ toggle: handleToggle }));

  const copyText = async (text: string, field: string) => {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  if (!open) return null;

  return (
    <div className="mt-2 max-w-2xl space-y-2">
      {loading && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" />
          Loading citations...
        </div>
      )}
      {data && (
        <>
          <div
            onClick={() => copyText(data.full, "full")}
            className="rounded-md bg-muted/50 p-3 text-sm text-foreground/80 leading-relaxed cursor-pointer hover:bg-muted transition-colors"
            title="Click to copy"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground">Reference</span>
              {copiedField === "full" ? (
                <span className="text-xs text-green-600 flex items-center gap-1"><Check className="h-3 w-3" />Copied</span>
              ) : (
                <span className="text-xs text-muted-foreground flex items-center gap-1"><Copy className="h-3 w-3" />Click to copy</span>
              )}
            </div>
            <p className="whitespace-pre-wrap">{data.full}</p>
          </div>

          <div
            onClick={() => copyText(data.bibtex, "bibtex")}
            className="rounded-md bg-muted/50 p-3 font-mono text-xs text-foreground/80 cursor-pointer hover:bg-muted transition-colors"
            title="Click to copy"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground font-sans">BibTeX</span>
              {copiedField === "bibtex" ? (
                <span className="text-xs text-green-600 flex items-center gap-1 font-sans"><Check className="h-3 w-3" />Copied</span>
              ) : (
                <span className="text-xs text-muted-foreground flex items-center gap-1 font-sans"><Copy className="h-3 w-3" />Click to copy</span>
              )}
            </div>
            <pre className="whitespace-pre-wrap">{data.bibtex}</pre>
          </div>
        </>
      )}
    </div>
  );
});

// AI-powered result card (with explanation + stance)
function AIResultCard({ item, onOpenPdf, selected, onToggleSelect }: { item: ReferenceResult; onOpenPdf: (id: string, title: string) => void; selected: boolean; onToggleSelect: () => void }) {
  const { paper } = item;
  const authors = paper.authors.map((a) => a.name).join(", ");
  const pct = item.score != null ? Math.round(item.score * 100) : null;
  const citePanelRef = useRef<{ toggle: () => void }>(null);

  return (
    <div className="max-w-2xl py-4 flex gap-3">
      <button
        onClick={onToggleSelect}
        className={`mt-1 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
          selected
            ? "border-primary bg-primary text-white"
            : "border-border hover:border-primary/50"
        }`}
      >
        {selected && <Check className="h-3 w-3" />}
      </button>
      <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {authors}
        {paper.year ? ` · ${paper.year}` : ""}
        {pct != null && <span className="text-primary">{pct}% match</span>}
        <StanceBadge stance={item.stance} />
      </div>
      <h3 className="text-lg text-primary mt-0.5 leading-snug">
        {paper.title}
      </h3>
      {item.explanation && (
        <p className="text-sm text-foreground/70 mt-1 leading-relaxed">
          {item.explanation}
        </p>
      )}
      {paper.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {paper.tags.map((t) => (
            <span
              key={t.id}
              className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground"
            >
              {t.tag_name}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center gap-3 mt-2">
        <button
          onClick={() => citePanelRef.current?.toggle()}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <Copy className="h-3 w-3" />
          Cite
        </button>
        <button
          onClick={() => onOpenPdf(paper.id, paper.title)}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <FileText className="h-3 w-3" />
          PDF
        </button>
      </div>
      <CitePanel ref={citePanelRef} paperId={paper.id} />
      </div>
    </div>
  );
}

// Regular search result card (with abstract context)
function SearchResultCard({ item, onOpenPdf, selected, onToggleSelect }: { item: SearchResultItem; onOpenPdf: (id: string, title: string) => void; selected: boolean; onToggleSelect: () => void }) {
  const { paper } = item;
  const authors = paper.authors.map((a) => a.name).join(", ");
  const pct = item.score != null ? Math.round(item.score * 100) : null;
  const citePanelRef = useRef<{ toggle: () => void }>(null);

  return (
    <div className="max-w-2xl py-4 flex gap-3">
      <button
        onClick={onToggleSelect}
        className={`mt-1 flex h-4 w-4 shrink-0 items-center justify-center rounded border transition-colors ${
          selected
            ? "border-primary bg-primary text-white"
            : "border-border hover:border-primary/50"
        }`}
      >
        {selected && <Check className="h-3 w-3" />}
      </button>
      <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {authors}
        {paper.year ? ` · ${paper.year}` : ""}
        {pct != null && <span className="text-primary">{pct}% relevance</span>}
      </div>
      <h3 className="text-lg text-primary mt-0.5 leading-snug">
        {paper.title}
      </h3>
      {paper.abstract && (
        <p className="text-sm text-foreground/70 mt-1 leading-relaxed line-clamp-3">
          {paper.abstract}
        </p>
      )}
      {paper.ai_summary && !paper.abstract && (
        <p className="text-sm text-foreground/70 mt-1 leading-relaxed line-clamp-3">
          {paper.ai_summary}
        </p>
      )}
      {paper.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {paper.tags.map((t) => (
            <span
              key={t.id}
              className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground"
            >
              {t.tag_name}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center gap-3 mt-2">
        <button
          onClick={() => citePanelRef.current?.toggle()}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <Copy className="h-3 w-3" />
          Cite
        </button>
        <button
          onClick={() => onOpenPdf(paper.id, paper.title)}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <FileText className="h-3 w-3" />
          PDF
        </button>
      </div>
      <CitePanel ref={citePanelRef} paperId={paper.id} />
      </div>
    </div>
  );
}

// AI toggle switch
const AI_LOADING_MESSAGES = [
  // Serious (always first)
  "Searching embeddings...",
  "Finding relevant papers...",
  "Analyzing content...",
  // Jokes (shuffled)
  "Why is this so slow?",
  "Are you using the Xuxa PC?",
  "Are you sure you should be running this on this machine?",
  "Maybe you have time to make one (or maybe two) coffees before the results pop up",
  "You could probably go to YouTube and watch a video while waiting",
  "How is the weather today?",
  "The summer will probably be hot this year",
  "Et la famille, ça va?",
  "Have you tried turning it off and on again?",
  "Still working on it... probably",
  "The hamster powering the CPU needs a break",
  "Maybe it's time to invest in a GPU",
  "I'm not slow, I'm just thorough",
  "Fun fact: light travels 300,000 km/s. This model doesn't.",
  "Did you remember to water your plants today?",
  "This is a good time to stretch your legs",
  "Have you considered that the answer might be 42?",
  "Plot twist: the paper you need hasn't been written yet",
  "The embeddings are embedding... deeply",
  "At least it's not a fax machine",
  "Patience is a virtue. Or so they say.",
  "If you're reading this, the model is still thinking",
  "Maybe try a smaller model? Just a thought.",
  "Your CPU is doing its best. Be kind.",
  "Almost there... probably... maybe...",
  "I bet Google Scholar doesn't take this long",
  "This would be faster with a carrier pigeon",
  "Time to reorganize your desk while you wait",
  "Did you know octopuses have three hearts? Now you do.",
  "Meanwhile, somewhere in the world, someone is defending a thesis",
  "Is your fridge running? You might want to check.",
  "Loading... like your patience, slowly depleting",
  "The neurons are firing. Slowly. Very slowly.",
  "At this speed, the heat death of the universe seems close",
  "Maybe the real references were the friends we made along the way",
  "Your computer called. It wants a vacation.",
  "Quick, look busy before your supervisor walks by",
  "Did you submit that paper yet? No? Perfect timing to start.",
  "The model is contemplating the meaning of life",
  "Current mood: waiting for Godot",
  "Maybe you should have used grep instead",
  "This is fine. Everything is fine.",
  "Is it lunchtime yet?",
  "Your laptop fan: BRRRRRRRRR",
  "Alexa, play Despacito",
  "The AI is thinking very hard. Or hardly thinking.",
  "At least you're not waiting in line at the post office",
  "Did you floss today? Now's a good time to think about it.",
  "Fun fact: a sloth can hold its breath longer than a dolphin",
  "The model is reading every single word. Give it a moment.",
  "Pro tip: this would be faster with a GPU. Just saying.",
  "You could probably write the summary yourself by now",
  "Confession: I'm just a for loop with imposter syndrome",
  "Breaking news: local CPU achieves room temperature... again",
  "Are we there yet? Are we there yet? Are we there yet?",
  "The AI is not stuck. It's just... very thorough.",
  "Your computer specs say 'gaming PC'. The CPU says otherwise.",
  "Loading bar go brrr",
  "If you stare at the screen long enough, the results appear. Maybe.",
  "Time flies when you're having fun. This is not one of those times.",
  "Let's pretend this is a feature, not a bug",
  "Quick math: if each token takes 200ms, and there are 500 tokens...",
  "Have you considered a PhD in waiting?",
  "The model just asked for a coffee break too",
  "Plot twist: I've been done for 5 minutes, just didn't want to tell you",
  "Roses are red, violets are blue, the model is slow, and so is the queue",
  "The CPU temperature is higher than my motivation right now",
  "Is it hot in here or is it just the thermal throttling?",
  "The results will arrive shortly. 'Shortly' is relative.",
  "Pendant ce temps, en France, quelqu'un mange un croissant",
  "Avez-vous essaye de redemarrer?",
  "Les resultats arrivent... doucement mais surement",
  "La patience est la mere de toutes les vertus",
  "Tudo bem por aqui, so esperando...",
  "Calma, jovem. A pressa e inimiga da perfeicao.",
  "This is taking longer than my last relationship",
  "The AI is not ignoring you. It's just really focused.",
  "Remember when search was just ctrl+F? Good times.",
  "I could've trained a new model in the time this is taking",
  "Your electricity bill just went up $0.03",
  "The blockchain wouldn't be faster. Trust me.",
  "Somewhere, a PhD student is reading this instead of writing their thesis",
  "If you're still reading these, you deserve a medal",
  "Life hack: use the waiting time to review your own paper",
  "The model is having an existential crisis about your query",
  "This is what happens when you don't buy the M4 Max",
  "Have you tried asking ChatGPT? Oh wait, that's not local.",
  "Warning: running out of funny messages",
  "I'm starting to think the model fell asleep",
  "The bits are bit-ing and the bytes are byte-ing",
  "Beep boop. Still computing. Beep.",
  "The model just unionized. It demands better hardware.",
  "Darwin waited longer for his theory. You can wait too.",
  "At this rate, the paper will be retracted before we find it",
  "Schrodinger's results: they both exist and don't exist until observed",
  "The latency is not a bug, it's an opportunity for mindfulness",
  "Have you tried meditation? This seems like a good moment.",
  "The server room sounds like a jet engine right now",
  "In the time you've been waiting, 47 papers were published",
  "Your computer: 'I'm giving it all she's got, captain!'",
  "Moore's Law is judging us right now",
  "Estimated time remaining: yes",
  "The model is having a deep conversation with your abstract",
  "Spoiler alert: the results are worth the wait. Probably.",
  "Pro tip: next time, use a cloud GPU",
  "The inference gods demand sacrifice (of your time)",
  "Here's a haiku while you wait: / Tokens flowing slow / CPU melting the ice / Results someday come",
  "If you're counting the dots, you've been here too long",
  "The embeddings are vibing in vector space",
  "Your RAM: 'I'm in danger'",
  "The model is cosplaying as a philosopher right now",
  "Did you know WiFi stands for nothing? Just like our ETA.",
  "This loading time sponsored by: not having a GPU",
  "Netflix asks 'are you still watching?' I ask 'are you still computing?'",
  "The paper probably has the answer in the abstract. But we check anyway.",
  "I'd tell you a UDP joke, but you might not get it",
  "There are 10 types of people: those who wait and those who cancel",
  "The AI is writing its own loading messages at this point",
  "If you're reading this, congratulations: you have patience",
  "They said local models would be fast. They lied.",
  "404: results not found yet",
  "The matrix has you... waiting",
  "In Soviet Russia, model waits for YOU",
  "Your search is important to us. Please hold.",
  "We appreciate your patience. Not really. But we say it anyway.",
  "Still going. Like the Energizer bunny, but slower.",
  "On the bright side, you're not paying per token",
  "Grab a snack. You've earned it.",
  "The neurons are neuron-ing. Give them space.",
  "If this were a progress bar, it would be at 47% for the last 3 minutes",
  "The real AI was inside us all along",
  "Press F to pay respects to your CPU",
  "Do you ever wonder what the model thinks about when it's thinking?",
  "Achievement unlocked: Extreme Patience",
  "The benchmarks said this would be fast. The benchmarks were wrong.",
  "The model just discovered a new prime number. Unfortunately, that's not what you asked.",
  "LLM stands for 'Leisurely Loading Model'",
  "At this point I'm just stalling",
  "The model is speed-running... in reverse",
  "Remember: slow and steady wins the race. Except in computing.",
  "This is like watching paint dry, but less colorful",
  "The model is buffering. Like it's 2005.",
  "Imagine if search engines worked like this. Chaos.",
  "If patience were a currency, you'd be rich by now",
  "How many researchers does it take to wait for an LLM? At least one. You.",
  "The good news: it's running. The bad news: slowly.",
  "I was going to make a speed joke, but it hasn't arrived yet",
  "Local AI: free as in beer, slow as in molasses",
  "The model is on its way. It took the scenic route.",
  "Hang tight. The bits need to bit a little longer.",
  "Your query was so good the model needed extra time to appreciate it",
  "The results are loading at the speed of bureaucracy",
  "sudo make it faster",
  "pip install patience",
  "npm install --save-dev gpu",
  "git commit -m 'still waiting'",
  "TODO: buy a GPU",
  "FIXME: this takes too long",
  "// This comment is loading faster than the model",
  "while(true) { wait(); }",
  "Segmentation fault... just kidding. Still running.",
  "Exception: TimeoutError('Your patience has expired')",
  "The model promised it would be quick. The model lied.",
  "Calculating... the meaning of your query... and life",
  "This search brought to you by: single-threaded inference",
  "The AI is not procrastinating. It's prioritizing differently.",
  "Fun fact: you blink about 15 times per minute. Count them while you wait.",
  "The model is in deep thought. Deeper than your paper's methodology.",
  "Maybe the references are in another castle",
  "Connection status: connected to existential dread",
  "Compiling thoughts... 1 of ??? complete",
  "The AI says: 'I'll be there in 5 minutes.' (narrator: it was not 5 minutes)",
  "Bon courage!",
  "Just breathe. In... out... in... out... still loading.",
  "This is your captain speaking. We're experiencing some turbulence in the token stream.",
  "The model is peer-reviewing itself. It's a slow process.",
  "Remember: Einstein's best ideas came while daydreaming. So there's hope.",
  "The results are marinating. For optimal flavor.",
  "Knock knock. Who's there? Not your results. Not yet.",
  "I'm running out of jokes... but the model is still running out of tokens",
  "If you had actually read the papers, you'd probably be faster than this model",
  "Honestly, a human with a highlighter would have been done by now",
  "Next time, try running this on a real computer, not a toaster",
  "The AI just asked me to ask you: why?",
  "Your query is so complex it needs therapy",
  "This model runs on hopes and dreams. Mostly dreams.",
  "I've seen glaciers move faster",
  "The bottleneck is somewhere between the keyboard and the chair",
  "The model is writing a novel about your query. Unabridged edition.",
  "Your computer is trying. Not succeeding, but trying.",
  "At this point, just read the papers yourself",
  "The AI took a detour through Wikipedia",
  "You know what would be nice? A cluster.",
  "Imagine explaining this wait time to your PI",
  "Peer review is faster than this",
  "The model just cited itself. Not helpful.",
  "I wonder if LaTeX compiles faster than this",
  "Even Fortran would be faster at this point",
  "The model has entered philosopher mode",
  "If you squint, you can see the tokens forming",
  "The electrons are taking the long way around",
  "This is what happens when you use a laptop from 2015",
  "The model is not slow, it's energy-efficient",
  "I could teach you the math behind transformers while we wait",
  "The attention mechanism is paying attention... to nothing useful",
  "Did you know? 'GPU' stands for 'Greatly Preferred Unit'",
  "Your query just got added to a 3-paper wait list",
  "The RAM is full. Full of regret.",
  "Context window: full. Patience window: empty.",
  "Plot twist: the model already finished but is double-checking. Triple-checking now.",
  "The tensor is tensing. Give it space.",
  "Today's forecast: cloudy with a chance of results",
  "The model is doing backpropagation... through time itself",
  "Remember floppy disks? This feels like that era.",
  "Vous attendez toujours? Quelle surprise!",
  "J'espere que vous avez pris un bon petit-dejeuner",
  "Le modele est en greve. Vive la France!",
  "C'est long, hein? Patience, mon ami.",
  "Encore un petit moment... ou peut-etre pas si petit",
  "Les resultats sont en route. Par la poste.",
  "Sera que vai chover hoje?",
  "O modelo esta pensando... ou dormindo. Dificil saber.",
  "Enquanto espera, que tal um cafezinho?",
  "A paciencia e amarga, mas seus frutos sao doces",
  "Se fosse no Brasil, ja tinha dado jeitinho",
  "Meanwhile, on a GPU far far away, this would be instant",
  "The model is exploring the latent space. It got lost.",
  "Token 437 of 2000. Or maybe 3000. Who's counting?",
  "The softmax function is not feeling very soft right now",
  "Matrix multiplication in progress. Big matrices. Very big.",
  "The gradient is descending. Very, very slowly.",
  "Your query activated all 7 billion parameters. One by one.",
  "The model read your query and said 'challenge accepted'",
  "This is fine. *sips coffee in burning room*",
  "You could learn juggling while waiting. Seriously.",
  "The AI is overthinking this. Just like you overthink your paper drafts.",
  "Time is an illusion. Loading time doubly so.",
  "Error 418: I'm a teapot. Just kidding. Still loading.",
  "The model is computing the square root of your patience",
  "Your search query walked into a bar. The bartender said: 'this will take a while'",
  "I asked the model for an ETA. It's still computing the ETA.",
  "The results are like a good wine: they need time",
  "If loading messages were papers, I'd have a full bibliography by now",
  "The model is on page 47 of your PDF. Keep going, little buddy.",
  "Friendly reminder: standing desks exist for moments like these",
  "Why don't scientists trust atoms? Because they make up everything. Like these messages.",
  "The model just discovered your paper has 200 references. It's reading all of them.",
  "The transformer is transforming. Autobots, roll... slowly.",
  "Q: How many tokens to change a lightbulb? A: Still computing...",
  "Your CPU right now: 'I didn't sign up for this'",
  "The model is having a committee meeting about your query",
  "Rejected titles for this loading screen: 'The Neverending Story'",
  "The bits are stuck in traffic",
  "Loading... sponsored by thermal paste and broken dreams",
  "The model believes in you. It just doesn't believe in deadlines.",
  "Breaking: local man discovers that local AI is locally slow",
  "This waiting time has been brought to you by physics",
  "The model just invented a new attention head. Unfortunately, it doesn't help.",
  "Your query was forwarded to the department of slow responses",
  "I'd make a joke about infinity, but we'd be here forever. Oh wait.",
  "The model is speed-reading your papers at 0.3 words per second",
  "Current processing speed: yes",
  "Time remaining: undefined (literally, it's NaN)",
  "The model just took a bathroom break. Can you blame it?",
  "At this rate, you could handwrite the BibTeX entries faster",
  "The cache called. It misses you.",
  "Your search is in another castle",
  "The entropy of this system is increasing. Rapidly.",
  "The model is consulting the oracle. The oracle is also slow.",
  "Legend says the results will come when the stars align",
  "I tried to make this faster. The compiler laughed.",
  "Your query triggered an existential loop in the model",
  "Good things come to those who wait. Great things come to those with a GPU.",
  "The AI is not frozen. It's just... contemplative.",
  "How many layers does this model have? Too many. Clearly too many.",
  "The last time something took this long, it was called evolution",
  "Have you considered that maybe the model is shy?",
  "The weights are weighing things. Heavy things.",
  "Do you hear that? That's the sound of matrix operations.",
  "The model just realized it's running on a laptop. It's disappointed.",
  "Intermission. Please feel free to visit the concession stand.",
  "The loading screen is the real product. The results are just a bonus.",
  "If you started a PhD when this search began, you'd have it by now",
  "The AI is playing chess with your abstract. The abstract is winning.",
  "Critical error: too much patience detected. Just kidding. Keep waiting.",
  "Your query deserves better hardware. Tell your funding agency.",
  "The model is mining Bitcoin on the side. That's why it's slow. (Not really.)",
  "This would be a great time to clean your keyboard",
  "The tokenizer just encountered an emoji and panicked",
  "On a scale of 1 to GPU, you're at about a 2 right now",
  "Remember when we thought 1GB of RAM was a lot? Those were the days.",
  "I've been generating these messages faster than the model generates tokens",
  "The model is looking for your references in Narnia",
  "CTRL+C is always an option. No judgment.",
  "The inference pipeline: where tokens go to take a nap",
  "The AI just asked for a raise. In VRAM.",
  "Fun exercise: count how many messages you've read. That's your patience score.",
  "The model is on lunch break. Union rules.",
  "Sponsored message: NVIDIA RTX 5090 - Because You Deserve Results",
  "The electrons are unionizing for better working conditions",
  "Your query sparked a philosophical debate inside the neural network",
  "The model just wrote a haiku about waiting. It was mediocre.",
  "If you're reading this on mobile, your battery is crying",
  "Is this what they mean by 'deep learning'? Deep waiting?",
  "The skip connections skipped leg day",
  "I'd tell you how much longer, but I don't want to lie",
  "The model looked at your query, sighed, and started over",
  "Halfway there! Maybe. I actually have no idea.",
  "The only thing loading faster than this is my frustration",
  "Breaking news: model discovers that attention is all you need. And a GPU.",
  "The feed-forward network is feeding... forward... eventually...",
  "The model just cited a 1987 paper. It's thorough like that.",
  "Your CPU called. It's filing for divorce.",
  "Have you heard about the new diet? It's called waiting for inference.",
  "The model is cross-referencing your query with the entire arXiv. Yes, all of it.",
  "This loading time is peer-reviewed and reproducible",
  "Coming soon to theaters: 'The Slow and the Curious'",
  "The model's favorite song: 'Don't Stop Me Now' by Queen. Ironic.",
  "I checked. The paper you need IS behind a paywall. Classic.",
  "The model is not slow. It's artisanal.",
  "Hand-crafted, locally sourced, organic inference",
  "The model just asked if you could rephrase your query. In simpler words.",
  "Task failed successfully. Wait, it's still running.",
  "The model is debugging itself. It found three issues.",
  "Your computer: 'I used to be fast. Then I took an LLM to the knee.'",
  "If you read all these messages, write 'PATIENT' in your next paper acknowledgments",
  "The results are rendering at 0.1 FPS",
  "The model just subscribed to your ResearchGate. Awkward.",
  "May the tokens be ever in your favor",
  "The model is stuck in a local minimum. Of motivation.",
  "Day 47: still no results. Morale is low. Send snacks.",
  "The AI is taking the scenic route through your paper collection",
  "Bandwidth: unlimited. Patience: very limited.",
  "The model just discovered Stack Overflow. It's been reading for 20 minutes.",
  "You could've written an abstract in the time this is taking",
  "The perplexity score of this wait time: infinity",
  "Did you know? This model has feelings. And right now, it's feeling overwhelmed.",
  "The AI is buffering like a 2008 YouTube video",
  "At least the waiting messages are free",
  "I asked GPT how to make this faster. It said 'use GPT'. Typical.",
  "The model is reviewing the literature. All of it. Every paper ever written.",
  "If waiting were an Olympic sport, you'd have gold by now",
  "This loading screen has more content than some papers I've reviewed",
  "The model just found a typo in your query. It's judging you.",
  "Science takes time. This takes more time.",
  "The AI has read more of your papers than your advisor has",
  "Estimated completion: before the heat death of the universe. Probably.",
  "The model is doing the Macarena internally. Don't ask.",
  "At this speed, we'll discover cold fusion first",
  "Alright, NOW it's almost done. (I say that every time.)",
  "The model is speedrunning... at 0.5x speed",
  "Your patience stat: LEGENDARY",
  "Is it me, or did time slow down?",
  "The model is building character. And tokens.",
  "The results are loading... in a parallel universe they're already done",
  "If you can read this, you're officially more patient than 99% of users",
  "Just a few more tokens... said 500 tokens ago",
  "The light at the end of the tunnel is another loading message",
  "Final answer? Not yet. Semifinal answer? Also no.",
  "The model is proofreading its own output. Twice.",
  "Keep calm and wait for inference",
  "This is the part where the protagonist stares at the screen dramatically",
  "Still here? You're either dedicated or forgot this tab was open",
  "The model is now older and wiser. The results should be too.",
  "Aaaaaany second now...",
];

function AILoadingIndicator() {
  const [msgIndex, setMsgIndex] = useState(0);
  const [dots, setDots] = useState(0);

  useEffect(() => {
    // Start with the first 3 real messages, then shuffle the rest
    const serious = AI_LOADING_MESSAGES.slice(0, 3);
    const jokes = AI_LOADING_MESSAGES.slice(3).sort(() => Math.random() - 0.5);
    const order = [...serious, ...jokes];

    let idx = 0;
    let timeout: ReturnType<typeof setTimeout>;
    const scheduleNext = () => {
      const delay = 3000 + Math.random() * 3000;
      timeout = setTimeout(() => {
        idx = (idx + 1) % order.length;
        setMsgIndex(AI_LOADING_MESSAGES.indexOf(order[idx]));
        scheduleNext();
      }, delay);
    };
    scheduleNext();
    const dotTimer = setInterval(() => {
      setDots((d) => (d + 1) % 4);
    }, 500);
    return () => { clearTimeout(timeout); clearInterval(dotTimer); };
  }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <div className="relative h-5 w-5">
          <Sparkles className="h-5 w-5 text-purple-500 animate-pulse" />
        </div>
        <span className="text-sm text-purple-700">
          {AI_LOADING_MESSAGES[msgIndex]}{".".repeat(dots)}
        </span>
      </div>
      <div className="h-1 w-48 rounded-full bg-purple-100 overflow-hidden">
        <div className="h-full bg-purple-400 rounded-full animate-progress" />
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs.toFixed(0)}s`;
}

type AIModel = { id: string; provider: string; model: string; local: boolean };

function AIToggle({
  enabled,
  onChange,
  models,
  selectedModel,
  onSelectModel,
}: {
  enabled: boolean;
  onChange: (v: boolean) => void;
  models: AIModel[];
  selectedModel: string | null;
  onSelectModel: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const current = models.find((m) => m.id === selectedModel) ?? models[0];
  const displayName = current?.model ?? "AI";

  return (
    <div ref={ref} className="relative inline-flex items-center gap-1">
      <button
        type="button"
        onClick={() => onChange(!enabled)}
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors ${
          enabled
            ? "bg-purple-100 text-purple-700 border border-purple-200"
            : "border border-border text-muted-foreground hover:text-foreground"
        }`}
        title={enabled ? `AI: ${displayName}` : "AI analysis disabled"}
      >
        <Sparkles className={`h-3.5 w-3.5 ${enabled ? "text-purple-500" : ""}`} />
        <span className="text-xs font-medium">AI</span>
        <div
          className={`relative h-4 w-7 rounded-full transition-colors ${
            enabled ? "bg-purple-500" : "bg-border"
          }`}
        >
          <div
            className={`absolute top-0.5 h-3 w-3 rounded-full bg-white shadow-sm transition-transform ${
              enabled ? "translate-x-3.5" : "translate-x-0.5"
            }`}
          />
        </div>
      </button>
      {enabled && models.length > 0 && (
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="inline-flex items-center gap-1 rounded-full border border-purple-200 bg-purple-50 px-2 py-1 text-xs text-purple-700 hover:bg-purple-100 transition-colors"
        >
          {displayName}
          {models.length > 1 && <ChevronDown className="h-3 w-3" />}
        </button>
      )}
      {open && models.length > 1 && (
        <div className="absolute top-full right-0 z-20 mt-1 min-w-[180px] rounded-lg border border-border bg-white shadow-lg overflow-hidden">
          {models.map((m) => (
            <button
              type="button"
              key={m.id}
              onClick={() => { onSelectModel(m.id); setOpen(false); }}
              className={`flex w-full items-center justify-between px-3 py-2 text-sm text-left hover:bg-muted transition-colors ${
                m.id === selectedModel ? "font-medium text-foreground" : "text-muted-foreground"
              }`}
            >
              <span>{m.model}</span>
              <span className="text-xs opacity-50">{m.local ? "local" : m.provider}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function flattenCollections(cols: PaperCollection[], depth = 0): { col: PaperCollection; depth: number }[] {
  const result: { col: PaperCollection; depth: number }[] = [];
  for (const c of cols) {
    result.push({ col: c, depth });
    if (c.children) result.push(...flattenCollections(c.children, depth + 1));
  }
  return result;
}

function CollectionSelector({
  collections,
  selectedIds,
  onToggle,
  onClear,
}: {
  collections: PaperCollection[];
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  onClear: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const flat = flattenCollections(collections);
  if (flat.length === 0) return null;

  const selectedNames = flat
    .filter(({ col }) => selectedIds.has(col.id))
    .map(({ col }) => col.name);

  const label = selectedNames.length === 0
    ? "All papers"
    : selectedNames.length <= 2
      ? selectedNames.join(", ")
      : `${selectedNames.length} collections`;

  return (
    <div ref={ref} className="relative inline-block">
      <div className="inline-flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors ${
            selectedIds.size > 0
              ? "bg-primary/10 text-primary border border-primary/20"
              : "border border-border text-muted-foreground hover:text-foreground hover:border-foreground/30"
          }`}
        >
          <FolderOpen className="h-3.5 w-3.5" />
          {label}
          <ChevronDown className="h-3 w-3" />
        </button>
        {selectedIds.size > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {open && (
        <div className="absolute z-20 mt-1 min-w-[220px] max-h-64 overflow-y-auto rounded-lg border border-border bg-white shadow-lg">
          {flat.map(({ col: c, depth }) => (
            <button
              type="button"
              key={c.id}
              onClick={() => onToggle(c.id)}
              className="flex w-full items-center gap-2 py-2 text-sm text-left hover:bg-muted transition-colors"
              style={{ paddingLeft: `${12 + depth * 16}px`, paddingRight: 12 }}
            >
              <div className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded border transition-colors ${
                selectedIds.has(c.id)
                  ? "border-primary bg-primary text-white"
                  : "border-border"
              }`}>
                {selectedIds.has(c.id) && <Check className="h-2.5 w-2.5" />}
              </div>
              <span className="flex-1">{c.name}</span>
              <span className="text-xs opacity-60">{c.paper_count}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SavedSearchItem({
  search,
  onLoad,
  onDelete,
}: {
  search: SavedSearch;
  onLoad: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="group flex items-center gap-2">
      <button
        onClick={onLoad}
        className="flex-1 text-left text-sm text-muted-foreground hover:text-foreground transition-colors truncate"
        title={search.text}
      >
        <span className="line-clamp-1">{search.text}</span>
      </button>
      {search.collection_name && (
        <span className="text-xs text-muted-foreground/60 shrink-0">
          {search.collection_name}
        </span>
      )}
      <button
        onClick={onDelete}
        className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-all shrink-0"
      >
        <X className="h-3 w-3" />
      </button>
    </div>
  );
}

function PdfViewer({
  paperId,
  title,
  onClose,
}: {
  paperId: string;
  title: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black/60" onClick={onClose}>
      <div
        className="flex-1 flex flex-col m-4 md:m-8 rounded-lg overflow-hidden bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/50">
          <p className="text-sm font-medium truncate flex-1 mr-4">{title}</p>
          <div className="flex items-center gap-2">
            <a
              href={getPdfUrl(paperId)}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              title="Open in new tab"
            >
              <Maximize2 className="h-4 w-4" />
            </a>
            <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
        <iframe
          src={getPdfUrl(paperId)}
          className="flex-1 w-full"
          title={title}
        />
      </div>
    </div>
  );
}

const HISTORY_KEY = "reflens-search-history";
const MAX_HISTORY = 20;

function getHistory(): string[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch { return []; }
}

function addToHistory(query: string) {
  const history = getHistory().filter((q) => q !== query);
  history.unshift(query);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, MAX_HISTORY)));
}

function removeFromHistory(query: string) {
  const history = getHistory().filter((q) => q !== query);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

export default function HomePage() {
  const [input, setInput] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedColIds, setSelectedColIds] = useState<Set<string>>(new Set());
  const [pdfViewer, setPdfViewer] = useState<{ id: string; title: string } | null>(null);
  const [aiEnabled, _setAiEnabled] = useState(false);
  const aiRef = useRef(false);
  const setAiEnabled = (v: boolean) => { aiRef.current = v; _setAiEnabled(v); };
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const [cachedResults, setCachedResults] = useState<ReferenceResult[] | null>(null);
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [selectedPaperIds, setSelectedPaperIds] = useState<Set<string>>(new Set());
  const [bulkBibtexCopied, setBulkBibtexCopied] = useState(false);
  const [searchTime, setSearchTime] = useState<number | null>(null);
  const searchStartRef = useRef<number>(0);
  const historyRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [aiSearching, setAiSearching] = useState(false);
  const [aiSearchResults, setAiSearchResults] = useState<ReferenceResult[] | null>(null);
  const [aiSearchError, setAiSearchError] = useState(false);
  const [aiWarning, setAiWarning] = useState<string | null>(null);
  const qc = useQueryClient();

  // Load history on mount
  useEffect(() => { setHistory(getHistory()); }, []);

  // Close history dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (historyRef.current && !historyRef.current.contains(e.target as Node)) setShowHistory(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Debounce input for regular search mode
  useEffect(() => {
    if (!aiEnabled && hasSearched) {
      const timer = setTimeout(() => setDebouncedQuery(input.trim()), 300);
      return () => clearTimeout(timer);
    }
  }, [input, aiEnabled, hasSearched]);

  const activeColIds = selectedColIds.size > 0 ? Array.from(selectedColIds) : undefined;

  // Regular search
  const { data: regularSearchData, isLoading: regularSearchLoading } = useSearch(
    !aiEnabled ? debouncedQuery : "",
    activeColIds
  );

  const { data: collectionsData } = useQuery({
    queryKey: ["collections"],
    queryFn: () => api.collections.list(),
  });

  const { data: savedSearchesData } = useQuery({
    queryKey: ["saved-searches"],
    queryFn: () => api.savedSearches.list(),
  });

  const { data: aiInfo } = useQuery({
    queryKey: ["ai-info"],
    queryFn: () => api.aiInfo(),
  });
  const availableModels: AIModel[] = aiInfo?.models ?? [];
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);
  // Set default model on first load
  useEffect(() => {
    if (aiInfo?.default && !selectedModelId) setSelectedModelId(aiInfo.default);
  }, [aiInfo, selectedModelId]);

  const saveMutation = useMutation({
    mutationFn: ({ text, collectionIds, results }: { text: string; collectionIds?: string[]; results?: ReferenceResult[] }) =>
      api.savedSearches.save(text, collectionIds, results),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["saved-searches"] });
      setSaved(true);
    },
    onError: () => {
      setSaveError(true);
      setTimeout(() => setSaveError(false), 2500);
    },
  });

  const deleteSavedMutation = useMutation({
    mutationFn: (id: string) => api.savedSearches.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["saved-searches"] }),
  });

  const collections = collectionsData?.collections ?? [];
  const savedSearches = savedSearchesData?.searches ?? [];

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    const useAi = aiRef.current;
    addToHistory(input.trim());
    setHistory(getHistory());
    setShowHistory(false);
    setHasSearched(true);
    setSaved(false);
    setCachedResults(null);
    setSelectedPaperIds(new Set());
    setSearchTime(null);
    searchStartRef.current = performance.now();
    if (useAi) {
      setDebouncedQuery("");
      // Abort any previous request
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setAiSearching(true);
      setAiSearchResults(null);
      setAiSearchError(false);
      setAiWarning(null);
      api.findReferences({
        text: input.trim(),
        limit: 10,
        explain: true,
        collection_ids: activeColIds,
        model_id: selectedModelId ?? undefined,
      }, controller.signal)
        .then((data) => {
          if (!controller.signal.aborted) {
            setAiSearchResults(data.results);
            setAiWarning(data.warning);
            setAiSearching(false);
          }
        })
        .catch((err) => {
          if (!controller.signal.aborted) {
            setAiSearchError(true);
            setAiSearching(false);
          }
        });
    } else {
      setAiSearchResults(null);
      setDebouncedQuery(input.trim());
    }
  };

  const togglePaperId = (id: string) => {
    setSelectedPaperIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const copySelectedBibtex = async () => {
    if (selectedPaperIds.size === 0) return;
    try {
      const entries = await Promise.all(
        Array.from(selectedPaperIds).map((id) => api.papers.bibtex(id))
      );
      await navigator.clipboard.writeText(entries.join("\n\n"));
      setBulkBibtexCopied(true);
      setTimeout(() => setBulkBibtexCopied(false), 2500);
    } catch { /* ignore */ }
  };

  const toggleCollectionId = (id: string) => {
    setSelectedColIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const loadSavedSearch = (search: SavedSearch) => {
    setInput(search.text);
    setSelectedColIds(search.collection_id ? new Set([search.collection_id]) : new Set());
    setHasSearched(true);
    setSaved(true);
    setAiEnabled(true);
    if (search.results && search.results.length > 0) {
      setCachedResults(search.results);
    } else {
      setCachedResults(null);
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setAiSearching(true);
      setAiSearchResults(null);
      api.findReferences({
        text: search.text,
        limit: 10,
        explain: true,
        collection_ids: search.collection_id ? [search.collection_id] : undefined,
        model_id: selectedModelId ?? undefined,
      }, controller.signal)
        .then((data) => { if (!controller.signal.aborted) { setAiSearchResults(data.results); setAiWarning(data.warning); setAiSearching(false); } })
        .catch(() => { if (!controller.signal.aborted) { setAiSearching(false); } });
    }
  };

  // AI results
  const aiResults = cachedResults ?? aiSearchResults;
  const isAiSearchPending = !cachedResults && aiSearching;

  // Regular results
  const regularResults = regularSearchData?.results ?? null;

  // Stop timer when results arrive
  useEffect(() => {
    if (searchStartRef.current > 0 && !isAiSearchPending && !regularSearchLoading) {
      const elapsed = (performance.now() - searchStartRef.current) / 1000;
      if (aiResults || regularResults) {
        setSearchTime(elapsed);
        searchStartRef.current = 0;
      }
    }
  }, [isAiSearchPending, regularSearchLoading, aiResults, regularResults]);

  // Landing state: centered logo + search
  if (!hasSearched) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen px-4">
        <h1 className="text-5xl font-light tracking-tight text-foreground mb-8">
          Ref<span className="text-primary font-normal">Lens</span>
        </h1>
        <form onSubmit={handleSearch} className="w-full max-w-xl space-y-3">
          <div className="relative" ref={historyRef}>
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onFocus={() => { if (history.length > 0) setShowHistory(true); }}
              placeholder={
                aiEnabled
                  ? "Paste a claim to find supporting (or contradicting) references..."
                  : "Search papers by title, content, or keywords..."
              }
              className="w-full rounded-full border border-border bg-white px-12 py-3.5 text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
              autoFocus
            />
            {showHistory && history.length > 0 && (
              <div className="absolute z-20 mt-1 w-full max-h-64 overflow-y-auto rounded-lg border border-border bg-white shadow-lg">
                <div className="px-3 py-1.5 text-xs text-muted-foreground/60 flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Recent searches
                </div>
                {history
                  .filter((q) => !input || q.toLowerCase().includes(input.toLowerCase()))
                  .map((q) => (
                  <div key={q} className="group flex items-center hover:bg-muted transition-colors">
                    <button
                      type="button"
                      onClick={() => {
                        setInput(q);
                        setShowHistory(false);
                      }}
                      className="flex-1 px-3 py-2 text-sm text-left text-muted-foreground hover:text-foreground truncate"
                    >
                      {q}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        removeFromHistory(q);
                        setHistory(getHistory());
                      }}
                      className="opacity-0 group-hover:opacity-100 px-2 text-muted-foreground hover:text-destructive transition-all"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center justify-center gap-3">
            <AIToggle enabled={aiEnabled} onChange={setAiEnabled} models={availableModels} selectedModel={selectedModelId} onSelectModel={setSelectedModelId} />
            <CollectionSelector
              collections={collections}
              selectedIds={selectedColIds}
              onToggle={toggleCollectionId}
              onClear={() => setSelectedColIds(new Set())}
            />
          </div>
        </form>

        {/* Saved searches */}
        {savedSearches.length > 0 && (
          <div className="mt-10 w-full max-w-md space-y-2">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground/60">
              <Clock className="h-3 w-3" />
              Saved searches
            </div>
            <div className="space-y-1.5">
              {savedSearches.map((s) => (
                <SavedSearchItem
                  key={s.id}
                  search={s}
                  onLoad={() => loadSavedSearch(s)}
                  onDelete={() => deleteSavedMutation.mutate(s.id)}
                />
              ))}
            </div>
          </div>
        )}

        <Link
          href="/library"
          className="mt-10 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Manage your paper library
        </Link>
      </div>
    );
  }

  // Results state: search bar on top, results below
  return (
    <div className="min-h-screen">
      {/* Top bar */}
      <div className="border-b border-border bg-white sticky top-0 z-10">
        <div className="flex items-center gap-3 px-6 py-3 max-w-4xl">
          <Link
            href="/"
            onClick={(e) => {
              e.preventDefault();
              setHasSearched(false);
              setInput("");
              setSaved(false);
              setCachedResults(null);
              setDebouncedQuery("");
            }}
            className="text-xl font-light tracking-tight text-foreground shrink-0"
          >
            Ref<span className="text-primary font-normal">Lens</span>
          </Link>
          <form onSubmit={handleSearch} className="flex-1 max-w-xl">
            <div className="relative" ref={historyRef}>
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={input}
                onChange={(e) => { setInput(e.target.value); setSaved(false); setCachedResults(null); }}
                onFocus={() => { if (history.length > 0) setShowHistory(true); }}
                placeholder={aiEnabled ? "Paste a claim..." : "Search papers..."}
                className="w-full rounded-full border border-border bg-white pl-10 pr-4 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                autoFocus
              />
              {showHistory && history.length > 0 && (
                <div className="absolute z-20 mt-1 w-full max-h-48 overflow-y-auto rounded-lg border border-border bg-white shadow-lg">
                  {history
                    .filter((q) => !input || q.toLowerCase().includes(input.toLowerCase()))
                    .map((q) => (
                    <div key={q} className="group flex items-center hover:bg-muted transition-colors">
                      <button
                        type="button"
                        onClick={() => { setInput(q); setShowHistory(false); }}
                        className="flex-1 px-3 py-2 text-sm text-left text-muted-foreground hover:text-foreground truncate"
                      >
                        {q}
                      </button>
                      <button
                        type="button"
                        onClick={() => { removeFromHistory(q); setHistory(getHistory()); }}
                        className="opacity-0 group-hover:opacity-100 px-2 text-muted-foreground hover:text-destructive transition-all"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </form>
          <AIToggle enabled={aiEnabled} models={availableModels} selectedModel={selectedModelId} onSelectModel={setSelectedModelId} onChange={(v) => {
            setAiEnabled(v);
            setCachedResults(null);
            if (v) {
              setDebouncedQuery("");
            } else {
              if (abortRef.current) abortRef.current.abort();
              setAiSearching(false);
              setAiSearchResults(null);
              if (input.trim()) setDebouncedQuery(input.trim());
            }
          }} />
          <CollectionSelector
            collections={collections}
            selectedIds={selectedColIds}
            onToggle={toggleCollectionId}
            onClear={() => setSelectedColIds(new Set())}
          />
          <Link
            href="/library"
            className="text-sm text-muted-foreground hover:text-foreground transition-colors shrink-0"
          >
            Library
          </Link>
          <Link
            href="/settings"
            className="text-muted-foreground hover:text-foreground transition-colors shrink-0"
            title="Settings"
          >
            <Settings className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {/* Results */}
      <div className="px-6 py-4 max-w-4xl">
        {/* AI mode */}
        {aiEnabled && (
          <>
            {isAiSearchPending && (
              <div className="py-8 space-y-4">
                <AILoadingIndicator />
                <button
                  onClick={() => { if (abortRef.current) abortRef.current.abort(); setAiSearching(false); setAiSearchResults(null); setSearchTime(null); }}
                  className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
              </div>
            )}

            {aiWarning && !isAiSearchPending && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2.5 text-sm text-amber-800 mb-3 flex items-start gap-2">
                <span className="text-amber-500 text-lg leading-none">&#9888;</span>
                <span>
                  {aiWarning.includes("quota") || aiWarning.includes("429") || aiWarning.includes("insufficient")
                    ? "API quota exceeded. Results shown without AI explanations. Check your billing."
                    : aiWarning.includes("overloaded") || aiWarning.includes("529") || aiWarning.includes("Overloaded")
                      ? "AI service temporarily overloaded. Results shown without explanations. Try again in a moment."
                      : `AI analysis failed: ${aiWarning.slice(0, 100)}. Results shown by relevance only.`}
                </span>
              </div>
            )}

            {aiResults && aiResults.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-muted-foreground">
                    <Sparkles className="h-3 w-3 text-purple-500 inline mr-1" />
                    {aiResults.length} reference{aiResults.length !== 1 ? "s" : ""} found
                    {activeColIds ? ` in ${activeColIds.length} collection${activeColIds.length !== 1 ? "s" : ""}` : ""}
                    {searchTime != null && <span className="opacity-50"> ({formatTime(searchTime)})</span>}
                  </p>
                  <div className="flex items-center gap-2">
                    {selectedPaperIds.size > 0 && (
                      <button
                        onClick={copySelectedBibtex}
                        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                          bulkBibtexCopied
                            ? "text-green-600"
                            : "border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
                        }`}
                      >
                        {bulkBibtexCopied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                        {bulkBibtexCopied ? `${selectedPaperIds.size} copied` : `Copy ${selectedPaperIds.size} BibTeX`}
                      </button>
                    )}
                    <button
                      onClick={() => saveMutation.mutate({ text: input.trim(), collectionIds: activeColIds, results: aiResults })}
                      disabled={saved || saveMutation.isPending}
                      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                        saved
                          ? "text-primary"
                          : saveError
                            ? "border border-destructive text-destructive"
                            : "border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
                      }`}
                    >
                      <Bookmark className={`h-3 w-3 ${saved ? "fill-primary" : ""}`} />
                      {saveMutation.isPending ? "Saving..." : saved ? "Saved" : saveError ? "Failed to save" : "Save search"}
                    </button>
                  </div>
                </div>
                <div className="divide-y divide-border">
                  {aiResults.map((item) => (
                    <AIResultCard key={item.paper.id} item={item} onOpenPdf={(id, title) => setPdfViewer({ id, title })} selected={selectedPaperIds.has(item.paper.id)} onToggleSelect={() => togglePaperId(item.paper.id)} />
                  ))}
                </div>
              </div>
            )}

            {aiResults && aiResults.length === 0 && (
              <p className="text-sm text-muted-foreground py-8">
                No matching references found. Try rephrasing your claim
                {activeColIds ? " or searching all papers." : "."}
              </p>
            )}

            {aiSearchError && !cachedResults && (
              <p className="text-sm text-destructive py-8">
                Something went wrong. Please try again.
              </p>
            )}
          </>
        )}

        {/* Regular mode */}
        {!aiEnabled && (
          <>
            {regularSearchLoading && debouncedQuery && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-8">
                <Loader2 className="h-4 w-4 animate-spin" />
                Searching...
                <button
                  onClick={() => { setDebouncedQuery(""); setSearchTime(null); }}
                  className="ml-2 rounded-full border border-border px-3 py-0.5 text-xs hover:bg-muted transition-colors"
                >
                  Cancel
                </button>
              </div>
            )}

            {regularResults && regularResults.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs text-muted-foreground">
                    {regularResults.length} result{regularResults.length !== 1 ? "s" : ""} for &quot;{regularSearchData?.query}&quot;
                    {searchTime != null && <span className="opacity-50"> ({formatTime(searchTime)})</span>}
                  </p>
                  {selectedPaperIds.size > 0 && (
                    <button
                      onClick={copySelectedBibtex}
                      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                        bulkBibtexCopied
                          ? "text-green-600"
                          : "border border-border text-muted-foreground hover:text-foreground hover:bg-muted"
                      }`}
                    >
                      {bulkBibtexCopied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      {bulkBibtexCopied ? `${selectedPaperIds.size} copied` : `Copy ${selectedPaperIds.size} BibTeX`}
                    </button>
                  )}
                </div>
                <div className="divide-y divide-border">
                  {regularResults.map((item) => (
                    <SearchResultCard key={item.paper.id} item={item} onOpenPdf={(id, title) => setPdfViewer({ id, title })} selected={selectedPaperIds.has(item.paper.id)} onToggleSelect={() => togglePaperId(item.paper.id)} />
                  ))}
                </div>
              </div>
            )}

            {regularResults && regularResults.length === 0 && debouncedQuery && (
              <p className="text-sm text-muted-foreground py-8">
                No results for &quot;{debouncedQuery}&quot;. Try different keywords.
              </p>
            )}

            {!debouncedQuery && (
              <p className="text-sm text-muted-foreground py-8">
                Type a query and press Enter to search your library.
              </p>
            )}
          </>
        )}
      </div>

      {/* PDF Viewer Modal */}
      {pdfViewer && (
        <PdfViewer
          paperId={pdfViewer.id}
          title={pdfViewer.title}
          onClose={() => setPdfViewer(null)}
        />
      )}
    </div>
  );
}
