import sys
import io

# Fix encoding for Windows Console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

from rag_pipeline_v3 import FundRAG

def main():
    print("==================================================")
    print("   基金从业知识 Copilot (CLI Mode)   ")
    print("   输入 'exit' 或 'quit' 退出")
    print("==================================================\n")

    print("正在初始化系统，请稍候...")
    try:
        rag = FundRAG()
        print("系统初始化完成！\n")
    except Exception as e:
        print(f"系统初始化失败: {e}")
        return

    while True:
        try:
            # Handle input encoding safely
            print("请输入题目/问题：")
            question = input("> ").strip()
            
            if question.lower() in ['exit', 'quit']:
                print("再见！")
                break
                
            if not question:
                continue
                
            print("\n正在思考中...\n")
            
            result = rag.query(question)
            
            print("-" * 50)
            print(result['full_response'])
            print("-" * 50)
            print("\n")
            
        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"\n发生错误: {e}\n")

if __name__ == "__main__":
    main()

