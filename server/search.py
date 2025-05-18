import argparse
import json
from server.vector_store import vector_store

def search_subtitles(query, n_results=5):
    """搜索字幕"""
    results = vector_store.search(query, n_results)
    
    # 打印结果
    print(f"\n搜索结果: '{query}'")
    print("-" * 50)
    
    for i, result in enumerate(results, 1):
        print(f"\n结果 {i}:")
        print(f"文本: {result['text']}")
        print(f"元数据: {json.dumps(result['metadata'], ensure_ascii=False, indent=2)}")
        if result['distance'] is not None:
            print(f"相似度: {1 - result['distance']:.4f}")
        print("-" * 30)

def main():
    parser = argparse.ArgumentParser(description='字幕搜索工具')
    parser.add_argument('query', help='搜索查询')
    parser.add_argument('-n', '--num-results', type=int, default=5,
                      help='返回结果数量 (默认: 5)')
    
    args = parser.parse_args()
    search_subtitles(args.query, args.num_results)

if __name__ == '__main__':
    main() 