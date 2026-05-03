import { useState } from 'react'
import { TagCloud } from 'react-tagcloud'
import './App.css'

function App() {
  const [text, setText] = useState('')
  const [words, setWords] = useState([])
  const [maxWords, setMaxWords] = useState(50)
  const [minLength, setMinLength] = useState(2)
  
  const placeholderText = `请在此输入要生成词云图的文字...

支持中英文混合文本。

示例：
人工智能是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。该领域的研究包括机器人、语言识别、图像识别、自然语言处理和专家系统等。人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大，可以设想，未来人工智能带来的科技产品，将会是人类智慧的"容器"。

Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to natural intelligence displayed by animals including humans. AI research has been defined as the field of study of intelligent agents, which refers to any system that perceives its environment and takes actions that maximize its chance of achieving its goals.`
  
  const stopWords = new Set([
    '的', '是', '在', '了', '和', '与', '或', '及', '等', '这', '那',
    '有', '为', '以', '于', '上', '下', '中', '之', '但', '而', '也',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
    'through', 'during', 'before', 'after', 'above', 'below', 'between',
    'and', 'but', 'if', 'or', 'because', 'until', 'while', 'although',
    'i', 'me', 'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his', 'she',
    'her', 'it', 'its', 'they', 'them', 'their', 'this', 'that', 'these',
    'those', 'am', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought',
    'used', 'so', 'such', 'too', 'very', 'just', 'also', 'now', 'then', 'here',
    'there', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
    'few', 'more', 'most', 'other', 'some', 'any', 'no', 'nor', 'not', 'only',
    'own', 'same', 'than', 'what', 'which', 'who', 'whom', 'whose', 'why',
    'out', 'off', 'up', 'down', 'over', 'under', 'again', 'further', 'once',
    'about', 'against', 'between', 'into', 'through', 'during', 'before',
    'after', 'above', 'below', 'from', 'up', 'down', 'in', 'out', 'on', 'off',
    'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there',
    'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most',
    'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
    'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should',
    'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', 'couldn',
    'didn', 'doesn', 'hadn', 'hasn', 'haven', 'isn', 'ma', 'mightn', 'mustn',
    'needn', 'shan', 'shouldn', 'wasn', 'weren', 'won', 'wouldn'
  ])

  const generateWordCloud = () => {
    if (!text.trim()) {
      alert('请输入一段文字')
      return
    }

    const wordCount = {}
    
    const chineseChars = text.match(/[\u4e00-\u9fa5]+/g) || []
    const englishWords = text.match(/[a-zA-Z]+/g) || []
    
    chineseChars.forEach(chars => {
      for (let i = 0; i < chars.length - 1; i++) {
        const char = chars[i]
        if (!stopWords.has(char) && char.length >= minLength) {
          wordCount[char] = (wordCount[char] || 0) + 1
        }
        if (i < chars.length - 1) {
          const twoChar = chars.substring(i, i + 2)
          if (!stopWords.has(twoChar) && !stopWords.has(twoChar[0]) && !stopWords.has(twoChar[1])) {
            wordCount[twoChar] = (wordCount[twoChar] || 0) + 1
          }
        }
      }
    })
    
    englishWords.forEach(word => {
      const lowerWord = word.toLowerCase()
      if (!stopWords.has(lowerWord) && lowerWord.length >= minLength) {
        wordCount[lowerWord] = (wordCount[lowerWord] || 0) + 1
      }
    })

    const wordList = Object.entries(wordCount)
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, maxWords)

    setWords(wordList)
  }

  const clearAll = () => {
    setText('')
    setWords([])
  }

  const customRenderer = (tag, size, color) => (
    <span
      key={tag.value}
      style={{
        fontSize: `${size}px`,
        color: color,
        margin: '3px',
        padding: '2px 4px',
        cursor: 'pointer',
        display: 'inline-block',
        transition: 'all 0.2s ease',
      }}
      className="word-tag"
      title={`${tag.value}: ${tag.count}次`}
      onMouseEnter={(e) => {
        e.target.style.transform = 'scale(1.1)'
        e.target.style.opacity = '0.8'
      }}
      onMouseLeave={(e) => {
        e.target.style.transform = 'scale(1)'
        e.target.style.opacity = '1'
      }}
    >
      {tag.value}
    </span>
  )

  return (
    <div className="app">
      <header className="header">
        <h1>词云图生成器</h1>
        <p>输入一段文字，生成精美的词云图</p>
      </header>

      <main className="main-content">
        <div className="input-section">
          <div className="control-group">
            <label>
              最大词数:
              <input
                type="number"
                min="10"
                max="200"
                value={maxWords}
                onChange={(e) => setMaxWords(parseInt(e.target.value))}
                className="number-input"
              />
            </label>
            <label>
              最小词长:
              <input
                type="number"
                min="1"
                max="10"
                value={minLength}
                onChange={(e) => setMinLength(parseInt(e.target.value))}
                className="number-input"
              />
            </label>
          </div>

          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={placeholderText}
            className="text-input"
          />

          <div className="button-group">
            <button onClick={generateWordCloud} className="btn btn-primary">
              生成词云图
            </button>
            <button onClick={clearAll} className="btn btn-secondary">
              清空
            </button>
          </div>
        </div>

        <div className="output-section">
          {words.length > 0 ? (
            <>
              <div className="wordcloud-container">
                <TagCloud
                  minSize={12}
                  maxSize={60}
                  tags={words}
                  renderer={customRenderer}
                  shuffle={false}
                />
              </div>
              <div className="stats">
                <p>共 {words.length} 个词</p>
                <p>词频最高: {words[0]?.value} ({words[0]?.count}次)</p>
              </div>
            </>
          ) : (
            <div className="placeholder">
              <div className="placeholder-icon">☁️</div>
              <p>输入文字并点击"生成词云图"按钮</p>
              <p className="hint">支持中英文混合文本</p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
