import ResultViewLayout from './ResultViewLayout'

const mHeaders = Array.from({ length: 24 }, (_, i) => `M${i + 1}`)

const ResultAllocationBalancePage = () => (
  <ResultViewLayout
    endpoint="/result-view/allocation-balance"
    title="中间表-分摊余额"
    columns={24}
    columnHeaders={mHeaders}
    description="账户册 + M1~M24 规划增量（余额），来自业务计划 plan_balance_i。"
  />
)

export default ResultAllocationBalancePage