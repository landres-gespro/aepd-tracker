// Cerebro semántico en segundo plano: no congela la interfaz
let embedder = null;

async function loadModel(){
    const T = await import('https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2/+esm');
    try {
        if (T.env && T.env.backends && T.env.backends.onnx && T.env.backends.onnx.wasm) {
            T.env.backends.onnx.wasm.numThreads = 1;
        }
    } catch(e){}
    embedder = await T.pipeline('feature-extraction', 'Xenova/paraphrase-multilingual-MiniLM-L12-v2', { quantized: true });
}

self.onmessage = async (e) => {
    const { cmd, text, reqId } = e.data;
    try {
        if (cmd === 'init') {
            if (!embedder) await loadModel();
            self.postMessage({ evt: 'ready', reqId });
        } else if (cmd === 'embed') {
            if (!embedder) await loadModel();
            const out = await embedder(text, { pooling: 'mean', normalize: true });
            self.postMessage({ evt: 'vector', reqId, vector: out.tolist()[0] });
        }
    } catch (err) {
        self.postMessage({ evt: 'error', reqId, msg: String(err) });
    }
};
