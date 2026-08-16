import ResultViewLayout from './ResultViewLayout'

const mHeaders = ['M0', ...Array.from({ length: 24 }, (_, i) => `M${i + 1}`)]

const ResultInterestNetIncomePage = () => (
  <ResultViewLayout
    endpoint="/result-view/interest-net-income"
    title="利息净收入测算表"
    columns={25}
    columnHeaders={mHeaders}
    description="账户册 + M0~M24 利息净收入 = 资产利息 - 负债利息（基于存量数据 rate 字段月度金额）。"
  />
)

export default ResultInterestNetIncomePage